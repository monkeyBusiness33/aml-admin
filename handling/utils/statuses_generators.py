from core.utils.datatables_functions import get_colored_circle


def get_fuel_booking_status_circle(status_code):
    circle_text = 'F'
    if status_code == 1:
        status_html = get_colored_circle(color='gray', text=circle_text, tooltip_text='No Fuel')
    elif status_code == 2:
        status_html = get_colored_circle(color='white', text=circle_text, tooltip_text='No action started')
    elif status_code == 3:
        status_html = get_colored_circle(color='yellow', text=circle_text, tooltip_text='Confirmed (No Fuel Release)')
    elif status_code == 4:
        status_html = get_colored_circle(color='green', text=circle_text,
                                         tooltip_text='Confirmed (DLA Contracted Location)')
    elif status_code == 5:
        status_html = get_colored_circle(color='green', text=circle_text, tooltip_text='Confirmed')
    else:
        status_html = get_colored_circle(color='black', text=circle_text, tooltip_text='Error')

    return status_html


def get_ground_handling_status_circle(status_code):
    circle_text = 'GH'
    if status_code == 1:
        status_html = get_colored_circle(color='white', text=circle_text, tooltip_text='No action started')
    elif status_code == 2:
        status_html = get_colored_circle(color='yellow', text=circle_text, tooltip_text='In Progress')
    elif status_code == 3:
        status_html = get_colored_circle(color='green', text=circle_text, tooltip_text='Confirmed')
    else:
        status_html = get_colored_circle(color='black', text=circle_text, tooltip_text='Error')

    return status_html
