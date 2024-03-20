function updateRequiredAttributeForUrlAndDescription() {
  let descriptionField = document.querySelector('#id_description');
  let urlField = document.querySelector('#id_url');
  let descriptionFieldLabel = document.querySelector('label[for="id_description"]');
  let urlFieldLabel = document.querySelector('label[for="id_url"]');

  if (!descriptionField.value) {
    urlFieldLabel.classList.add('required');
  } else {
    urlFieldLabel.classList.remove('required');
  }

  if (!urlField.value) {
    descriptionFieldLabel.classList.add('required');
  } else {
    descriptionFieldLabel.classList.remove('required');
  }
}

document.querySelector('#id_description')
  .addEventListener('input', updateRequiredAttributeForUrlAndDescription);
document.querySelector('#id_url')
  .addEventListener('input', updateRequiredAttributeForUrlAndDescription);

updateRequiredAttributeForUrlAndDescription()
