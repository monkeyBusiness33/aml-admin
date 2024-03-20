// send_pricing_update_request.js

// Update display of selected locations
setTimeout(() => {
  let el = document.querySelector('[id$="locations"]');
  $(el).djangoSelect2("destroy");
  $(el).djangoSelect2({
    dropdownParent: $(el).nextSibling,
    width: '100%',
    templateSelection: formatSelected,
  })
}, 200)

function formatSelected(item) {
  let selectionText = item.text.match(/\((?<test>.*)\)$/);
  return $('<span>' + selectionText[1] + '</span>');
}

