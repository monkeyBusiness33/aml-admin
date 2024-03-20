from django.shortcuts import render
from django.views.generic import TemplateView
from user.mixins import AdminPermissionsMixin


class CalendarView(AdminPermissionsMixin, TemplateView):
    template_name = 'team_calendar.html'
    permission_required = ['handling.p_view'] # TODO


class ScheduleListView(AdminPermissionsMixin, TemplateView):
    template_name = 'team_schedule.html'
    permission_required = ['handling.p_view'] # TODO
