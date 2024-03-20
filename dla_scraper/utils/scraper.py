from collections import defaultdict
from core.tasks import send_email
from datetime import date, datetime, timedelta
from decouple import config
from django.http import JsonResponse
from django.template.loader import render_to_string
from dla_scraper.models import *
from organisation.models import AirportDetails, Organisation
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

import json
import re
import time

def scrape_data(driver, url):
    # Load the page
    driver.get(url + 'Ipcis')

    # Wait until length selector and table fully loaded
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, '//select[@name="report_length"]')),
        EC.presence_of_element_located((By.XPATH, '//table[@id="report"]/tbody/tr[10]'))
    )

    # Clear stored requests
    del driver.requests

    # Switch to 100 items per page
    len_sel = driver.find_element(By.XPATH, '//select[@name="report_length"]')
    len_sel_obj = Select(len_sel)
    len_sel_obj.select_by_value("100");

    # Wait a bit for page to reload
    time.sleep(3)

    next_clickable = True
    result_dicts = []

    while (next_clickable):
        # Wait until table fully loaded
        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, '//div[@id="report_info"]')),
            EC.presence_of_element_located((By.XPATH, '//table[@id="report"]/tbody/tr[1]'))
        )

        [first_shown, last_shown, total_rows] = re.findall(r'(\d+)', driver.find_element(By.XPATH,
                                                                                         '//div[@id="report_info"]').text)
        requirements_request = None
        rows_shown = int(last_shown) - int(first_shown) + 1

        for request in driver.requests:
            if 'Requirements' in request.url and request.response:
                requirements_request = request

        # If request not yet completed, wait for it
        if requirements_request is None:
            try:
                requirements_request = driver.wait_for_request('Requirements', timeout=20)
            except TimeoutException as e:
                raise e

        body = requirements_request.response.body.decode('utf-8')
        data = json.loads(body)
        rows = data['data']

        # Delete elements that sometimes obscure buttons
        panel = driver.find_elements(By.CLASS_NAME, 'panel-wrapper')
        if panel:
            driver.execute_script("""var element = arguments[0];
                                          element.parentNode.removeChild(element);""", panel[0])

        result_dicts.extend(rows[-rows_shown:])

        # Clear stored requests
        del driver.requests

        # Try for next page
        next_btn = driver.find_element(By.ID, 'report_next')
        next_clickable = 'disabled' not in next_btn.get_attribute('class')

        if next_clickable:
            next_btn.click()

            # Wait a bit for page to reload
            time.sleep(3)

    if len(result_dicts) != int(total_rows):
        raise Exception("Not all rows could be scraped successfully")

    # Scrape IPA details from individual pages
    for dict in result_dicts:
        # Get additional parameters for VendorInfo url
        [vname, cindx, icao] = re.search(
            r'data-vname="([^\"]*).*data-cindx="([^\"]*)".*data-icao="([^\"]*)"',
            dict['vendor_name']
        ).groups()

        # Cleanup vendor name
        dict['vendor_name'] = re.sub(r'<[^\>]*>', '', dict['vendor_name'])

        # Get IPA name
        driver.get(url + f'VendorInfo?vendor={vname}&ci={cindx}&icao={icao}')

        # Wait until page fully loaded
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, '//form')),
        )
        content = driver.find_element(By.XPATH, '//form').text
        name_match = re.search(r'Name:[^\S\r\n]*(.*)', content)
        dict['ipa_name'] = name_match.group(1) if name_match else None

    return result_dicts


def cleanup_name(name):
    # Remove commas, full stops and multiple spaces
    if name:
        name = re.sub(r'[\.\,]', '', name)
        name = re.sub(' +', ' ', name).strip()

    return name


def reconcile_org_name(org, name_id):
    names = DLASupplierName.objects.filter(pk=name_id)

    # Link CIS DLA names with organisation
    if names:
        name = names.first()
        name.supplier = org
        name.save()

        # Update the contracts table with the supplier id
        for c in name.dla_contracts_using_supplier_name.all():
            c.supplier = org
            c.save()

        # Update the contracts table with the IPA id
        for c in name.dla_contracts_using_ipa_name.all():
            c.ipa = org
            c.save()


def run_dla_scraper(scheduled=False):
    url = config('CIS_URL', default=None)

    # Set up browser
    options = Options()
    options.add_argument("-headless")

    driver = webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install()),
        options=options
    )

    # Remote Firefox setup (only tested locally)
    # driver = webdriver.Remote(
    #     command_executor='http://127.0.0.1:4444',
    #     options=options
    # )

    attempt = 0

    while attempt < 3:
        try:
            contracts_raw = scrape_data(driver, url)
            break
        except Exception as e:
            time.sleep(5)
            attempt += 1

            if attempt == 3:
                driver.quit()

                DLAScraperRun.objects.create(
                    status=DLAScraperRunStatus.objects.get(code='ERROR'),
                    log={
                        'exception_type': type(e).__name__,
                        'exception_msg': str(e)
                    },
                    is_scheduled=scheduled
                )

                return

            continue

    driver.quit()

    log = defaultdict(list)

    # Get all vendor and IPA names and check if all present in organisations_dla_suppliers_ids
    existing_vendor_names = DLASupplierName.objects.values_list('name', flat=True)
    vendor_names = set(map(lambda x: x['vendor_name'], contracts_raw))
    vendor_names = vendor_names.union(set(map(lambda x: x['ipa_name'], contracts_raw)))
    cleaned_vendor_names = [cleanup_name(name) for name in vendor_names]
    new_vendor_names = set([name for name in cleaned_vendor_names if name and name not in existing_vendor_names])

    if new_vendor_names:
        log['new_vendor_names'] = list(new_vendor_names)

        for vendor_name in new_vendor_names:
            if vendor_name:
                DLASupplierName.objects.create(name=vendor_name)

    # Group all contracts by reference (contract + location)
    def constant_factory():
        return {
            'entries': list(),
            'line_items': list(),
            'icao': None
        }

    contracts = defaultdict(constant_factory)

    for con in contracts_raw:
        ref = f"{con['contract']}-{con['icao']}"
        contracts[ref]['entries'].append(con)
        contracts[ref]['line_items'].extend(con['list'])
        contracts[ref]['icao'] = con['icao']
        contracts[ref]['vendor_name'] = con['vendor_name']
        contracts[ref]['ipa_name'] = con['ipa_name']

    today = date.today()

    for c in contracts:
        commit_to_db = True
        con = contracts[c]
        con_obj = DLAContract()
        con_obj.contract_reference = c
        existing_contract = DLAContract.objects.filter(contract_reference=c).first()

        # Clean dates in each line item
        line_items = con['line_items']

        try:
            for item in line_items:
                if (item['contract_period']):
                    dates = re.findall(r'<.*>([\d\/]*) - ([\d\/]*)<.*>', item['contract_period'])[0]
                    item['start_date'] = datetime.strptime(dates[0], '%m/%d/%y').strftime('%Y-%m-%d')
                    item['end_date'] = datetime.strptime(dates[1], '%m/%d/%y').strftime('%Y-%m-%d')

            # Get dates (if multiple line items exist, pick outermost dates)
            con_obj.start_date = min([i['start_date'] for i in line_items if 'start_date' in i])
            con_obj.end_date = max([i['end_date'] for i in line_items if 'end_date' in i])

            # If end date in the past, set to inactive
            con_obj.is_active = True if con_obj.end_date > today.strftime('%Y-%m-%d') else False

            # Get location (airport) id
            airport = AirportDetails.objects.filter(icao_code__iexact=con['icao'])
        except:
            commit_to_db = False
            log['missing_dates'].append(con_obj.contract_reference)

        if not airport:
            # Check against alternative ICAO table
            alt_icao_for = DLALocationAlternativeIcaoCode.objects.filter(icao_code__iexact=con['icao'])

            if alt_icao_for and alt_icao_for.first().location:
                airport = AirportDetails.objects.filter(organisation=alt_icao_for.first().location)

        if airport:
            con_obj.location = airport.first().organisation
        else:
            commit_to_db = False
            log['missing_location'].append(con_obj.contract_reference)

        # Get supplier
        supplier_names = DLASupplierName.objects.filter(name=cleanup_name(con['vendor_name']))

        supplier_name = supplier_names.first() if supplier_names else None
        con_obj.cis_supplier_name = supplier_name
        supplier_update = False

        if supplier_name and supplier_name.supplier:
            supplier_update = existing_contract and existing_contract.supplier != supplier_name.supplier

            if supplier_update:
                con_obj.supplier = existing_contract.supplier
            else:
                con_obj.supplier = supplier_name.supplier
        elif supplier_name and existing_contract:
            # Reconcile the new name to the same supplier
            supplier_name.supplier = existing_contract.supplier
            supplier_name.save()
            con_obj.supplier = supplier_name.supplier
        else:
            log['missing_supplier'].append(con_obj.contract_reference)

        # Create a pending update if needed
        if supplier_update:
            update_exists = DLAScraperPendingOrganisationUpdate.objects.filter(
                is_ipa=False,
                contract=existing_contract,
                current_organisation=existing_contract.supplier,
                proposed_organisation=supplier_name.supplier
            ).exists()

            if not update_exists:
                DLAScraperPendingOrganisationUpdate.objects.create(
                    is_ipa=False,
                    contract=existing_contract,
                    current_organisation=existing_contract.supplier,
                    proposed_organisation=supplier_name.supplier
                )

        # Get IPA
        ipa_names = DLASupplierName.objects.filter(name=cleanup_name(con['ipa_name']))

        ipa_name = ipa_names.first() if ipa_names else None
        con_obj.cis_ipa_name = ipa_name
        ipa_update = False

        if ipa_name and ipa_name.supplier:
            ipa_update = existing_contract and existing_contract.ipa != ipa_name.supplier

            if ipa_update:
                con_obj.ipa = existing_contract.ipa
            else:
                con_obj.ipa = ipa_name.supplier
        elif ipa_name and existing_contract:
            # Reconcile the new name to the same IPA
            ipa_name.supplier = existing_contract.ipa
            ipa_name.save()
            con_obj.ipa = ipa_name.supplier
        elif existing_contract and not ipa_name:
            # In some cases, there is no IPA on the CIS website, but we want to keep the one assigned to contract
            ipa_update = existing_contract.ipa is not None

            if ipa_update:
                con_obj.ipa = existing_contract.ipa
        else:
            log['missing_ipa'].append(con_obj.contract_reference)

        # Create a pending update if needed
        if ipa_update:
            update_exists = DLAScraperPendingOrganisationUpdate.objects.filter(
                is_ipa=True,
                contract=existing_contract,
                current_organisation=existing_contract.ipa,
                proposed_organisation=ipa_name.supplier if ipa_name else None
            ).exists()

            if not update_exists:
                DLAScraperPendingOrganisationUpdate.objects.create(
                    is_ipa=True,
                    contract=existing_contract,
                    current_organisation=existing_contract.ipa,
                    proposed_organisation=ipa_name.supplier if ipa_name else None
                )

        # Check if reference already exists, update or create, log changes
        if commit_to_db:
            if not existing_contract:
                con_obj.save()
                log['new_contracts'].append(str(con_obj))
            else:
                # Check if something has changed and record details of changes
                changes = {}

                if str(con_obj.start_date) != str(existing_contract.start_date):
                    changes['start_date'] = [
                        str(existing_contract.start_date),
                        str(con_obj.start_date)
                    ]
                    existing_contract.start_date = con_obj.start_date

                if str(con_obj.end_date) != str(existing_contract.end_date):
                    changes['end_date'] = [
                        str(existing_contract.end_date),
                        str(con_obj.end_date)
                    ]
                    existing_contract.end_date = con_obj.end_date

                if con_obj.is_active != existing_contract.is_active:
                    changes['is_active'] = [existing_contract.is_active, con_obj.is_active]
                    existing_contract.is_active = con_obj.is_active

                if con_obj.location != existing_contract.location:
                    changes['location'] = [str(existing_contract.location), str(con_obj.location)]
                    existing_contract.location = con_obj.location

                if con_obj.supplier != existing_contract.supplier:
                    changes['supplier'] = [str(existing_contract.supplier), str(con_obj.supplier)]
                    existing_contract.supplier = con_obj.supplier

                if con_obj.ipa != existing_contract.ipa:
                    changes['ipa'] = [str(existing_contract.ipa), str(con_obj.ipa)]
                    existing_contract.ipa = con_obj.ipa

                if con_obj.cis_supplier_name != existing_contract.cis_supplier_name:
                    changes['cis_supplier_name'] = [str(existing_contract.cis_supplier_name), str(con_obj.cis_supplier_name)]
                    existing_contract.cis_supplier_name = con_obj.cis_supplier_name

                if con_obj.cis_ipa_name != existing_contract.cis_ipa_name:
                    changes['cis_ipa_name'] = [str(existing_contract.cis_ipa_name), str(con_obj.cis_ipa_name)]
                    existing_contract.cis_ipa_name = con_obj.cis_ipa_name

                if changes:
                    existing_contract.save()
                    log['changed_contracts'].append({con_obj.contract_reference: changes})

    # Check existing contracts against the new list to find any that have been removed
    existing_contracts = DLAContract.objects.filter(early_termination_date=None).all()
    new_contract_list = list(contracts.keys())
    removed_contracts = []
    expiring_contracts = []

    for ec in existing_contracts:
        if ec.contract_reference not in new_contract_list:
            removed_contracts.append(ec)
            log['removed_contracts'].append(str(ec))
            ec.early_termination_date = today.strftime('%Y-%m-%d')
            ec.is_active = False
            ec.save()
        elif ec.end_date - today == timedelta(days=1) and not ec.expiring_email_sent:
            expiring_contracts.append(ec)

    # Create scraper run log entry
    status_code = 'WARNING' if 'missing_dates' in log or 'missing_location' in log or 'missing_supplier' in log \
                               or 'new_contracts' in log or 'changed_contracts' in log or 'removed_contracts' in log \
                               or 'new_vendor_names' in log or 'missing_ipa' in log else 'OK'
    DLAScraperRun.objects.create(
        status=DLAScraperRunStatus.objects.get(code=status_code),
        log=log,
        is_scheduled = scheduled
    )

    # Send an email notification if location becomes uncontracted
    locations = set()

    # Early terminations
    for rc in removed_contracts:
        if not rc.location.dla_contracted_locations_here.filter(is_active=True).exists():
            locations.add(rc.location)

    # Expirations (send the day before expiration date)
    for xc in expiring_contracts:
        if not xc.location.dla_contracted_locations_here.filter(is_active=True, end_date__gt=today + timedelta(days=1)).exists():
            locations.add(xc.location)
            xc.expiring_email_sent = True
            xc.save()

    if locations:
        subject = 'DLA Contract Scraper Notification - New Uncontracted Location'
        body = render_to_string(
            'email/dla_new_uncontracted_location.html',
            {
                'cis_url': config('CIS_URL') + 'Ipcis',
                'locations': locations
            }
        )

        send_email(
            subject=subject,
            body=body,
            recipient=['contracts@amlglobal.net'],
        )
