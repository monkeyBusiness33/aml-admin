"use strict";
const d = document;

d.addEventListener("DOMContentLoaded", function (event) {

  const swalWithBootstrapButtons = Swal.mixin({
    customClass: {
      confirmButton: 'btn btn-primary me-3',
      cancelButton: 'btn btn-gray'
    },
    buttonsStyling: false
  });

  // options
  const breakpoints = {
    sm: 540,
    md: 720,
    lg: 960,
    xl: 1140
  };

  var sidebar = document.getElementById('sidebarMenu');
  window.sidebarTemporaryContracted = false;


  var content = document.getElementsByClassName('content')[0];
  if (sidebar && d.body.clientWidth < breakpoints.lg) {
    sidebar.addEventListener('shown.bs.collapse', function () {
      document.querySelector('body').style.position = 'fixed';
    });
    sidebar.addEventListener('hidden.bs.collapse', function () {
      document.querySelector('body').style.position = 'relative';
    });
  }

  var iconNotifications = d.querySelector('.notification-bell');
  if (iconNotifications) {
    iconNotifications.addEventListener('shown.bs.dropdown', function () {
      iconNotifications.classList.remove('unread');
    });
  }

  var scroll = new SmoothScroll('a[href*="#"]', {
    speed: 500,
    speedAsDuration: true
  });

  if (sidebar) {
    if (localStorage.getItem('sidebar') === 'contracted') {
      sidebar.classList.add('notransition');
      content.classList.add('notransition');

      sidebar.classList.add('contracted');

      setTimeout(function () {
        sidebar.classList.remove('notransition');
        content.classList.remove('notransition');
      }, 500);

    } else {
      sidebar.classList.add('notransition');
      content.classList.add('notransition');

      sidebar.classList.remove('contracted');

      setTimeout(function () {
        sidebar.classList.remove('notransition');
        content.classList.remove('notransition');
      }, 500);
    }

    var sidebarToggle = d.getElementById('sidebar-toggle');
    sidebarToggle.addEventListener('click', function () {
      if (sidebar.classList.contains('contracted')) {
        sidebar.classList.remove('contracted');
        localStorage.removeItem('sidebar');
        window.sidebarTemporaryContracted = false
      } else {
        sidebar.classList.add('contracted');
        localStorage.setItem('sidebar', 'contracted');
      }
    });

    sidebar.addEventListener('mouseenter', function () {
      if (localStorage.getItem('sidebar') === 'contracted' || sidebarTemporaryContracted === true) {
        if (sidebar.classList.contains('contracted')) {
          sidebar.classList.remove('contracted');
        }
      }
    });

    sidebar.addEventListener('mouseleave', function () {
      if (localStorage.getItem('sidebar') === 'contracted' || window.sidebarTemporaryContracted === true) {
        if (!sidebar.classList.contains('contracted')) {
          sidebar.classList.add('contracted');
        }
      }
    });

    // Keep sidebar opened while mouse hovering it
    sidebar.addEventListener('mouseover', function () {
      if (sidebar.classList.contains('contracted')) {
        sidebar.classList.remove('contracted');
      }
    });
  }

});
