// Run on first modal initialization only
if (typeof taxLabelSpans == 'undefined') {
  let taxResultsWrapper;
  var prevWidth = 0;
}

taxResultsWrapper = $('.taxes-results-wrapper');

resizeObserver = new ResizeObserver((entries) => {
  // Only react to changes in width (otherwise it's an infinite loop)
  for (const entry of entries) {
    const width = entry.borderBoxSize?.[0].inlineSize;
    if (typeof width === 'number' && width !== prevWidth) {
      prevWidth = width;

      $('.tax-label-long').each(function (i, el) {
        let unitSpan = $(el).find('.tax-unit');
        let parentWidth = $(el).closest('.flex-column').width();

        unitSpan.css('white-space', 'nowrap');
        if (unitSpan.width() > parentWidth) {
          unitSpan.css('white-space', 'normal');
        } else {
          unitSpan.css('white-space', 'nowrap');
        }
      });
    }
  }
});

taxResultsWrapper.each(function (i, el) {
  resizeObserver.observe(el)
});

load_tooltips();
