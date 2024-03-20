$('#modal').on('show.bs.modal', function () {
  $('.modal-backdrop').addClass('top-backdrop');
});

$('#modal').on('hide.bs.modal', function () {
  $('.modal-backdrop').removeClass('top-backdrop');
});
