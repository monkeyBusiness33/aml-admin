// Add CRM Activity modal datetime field timezone processing
var crm_activity_local_datetime_field = document.getElementById("id_organisation_people_activity_form_pre-datetime_local")
if (crm_activity_local_datetime_field) {
  crm_activity_local_datetime_field.oninput = function () {
    console.log('aaaa')
    var datetimeLocal = document.getElementById("id_organisation_people_activity_form_pre-datetime_local").value;
    var datetimeLocal = new Date(datetimeLocal.replace(/-/g, '/').replace('T', ' '));
    var datetimeUTC = moment.utc(datetimeLocal).format("YYYY-MM-DD HH:mm:ss");
    document.getElementById("id_organisation_people_activity_form_pre-datetime").value = datetimeUTC;
  }
}
