let org_type = document.querySelector('.org-details-navbar').dataset.orgType;
let nav_buttons = document.querySelectorAll('.org-details-navbar button')
let editBtn = document.querySelector('#org-edit-details-btn');
let editAnchor = ''
if (editBtn) {
  editAnchor = editBtn.querySelector('a');
}

nav_buttons.forEach(button => {
  button.addEventListener('click', alterPageDisplay)
})

let active_section = localStorage.getItem(`${org_type}-active_section`)

// Check whether the user navigated to the page or refreshed
let isNavigation = performance.getEntriesByType('navigation')[0]['type'] === 'navigate';

// Click the most relevant btn depending on user's origin (if navigated to page),
// or stored active section, or first tab from the left if absent
if (isNavigation && typeof activeTabFromOrigin !== 'undefined' && activeTabFromOrigin) {
  document.getElementById(activeTabFromOrigin).click();
  activeTabFromOrigin = '';
} else if (document.getElementById(active_section)) {
  document.getElementById(active_section).click();
} else {
  firstBtn = document.querySelector('.nav-button.order-first') || document.querySelector('.nav-button');
  firstBtn.click();
  localStorage.removeItem(`${org_type}-active_section`);
}

function alterPageDisplay() {
  let active_button = document.querySelector('.org-details-navbar .active')

  if (active_button) {
    let section = document.querySelector(`#${active_button.id}-container`)
    section.classList.add('d-none')
    active_button.classList.remove('active')
  }

  this.classList.add('active')
  let section = document.querySelector(`#${this.id}-container`)
  section.classList.remove('d-none')
  localStorage.setItem(`${org_type}-active_section`, this.id)

  // Update the display and URL of edit button
  let editUrl = null;

  if (typeof editBtnData !== 'undefined') {
    editUrl = editBtnData[this.id]

    if (editAnchor) {
      editAnchor.href = editUrl || '';
    }

    if (!editUrl) {
      editBtn.classList.add('d-none');
    } else {
      editBtn.classList.remove('d-none');
    }

  }

  if (section.querySelectorAll('.django-select2:has(+.select2-container)').length) {
    // Opening a modal breaks select2 fields, so just in case
    // reinit them when switching to a tab containing some
    section.querySelectorAll('.django-select2:has(+.select2-container)').forEach(field => {
      reInitializeField(field)
    });
  }
}


function reInitializeField(field) {
  $(field).djangoSelect2({
    dropdownParent: $(field).parent(),
    width: '100%',
  });
}
