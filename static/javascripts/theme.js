// Theme custom js methods
$(document).ready(function(){

  var addYearSelectorCustomLabels = function(){
    var lang = $('html').attr('lang')
    var extended = {
      'es': 'prorrogado',
      'en': 'extended',
    };
    var pendingApproval = {
      'es': 'proyecto',
      'en': 'proposal',
    };
    var yearLabels = {
      '2019': extended,
      '2020': extended,
      '2022': pendingApproval
    }

    $('.data-controllers .layout-slider .slider .slider-tick-label').each(function(){
      var year = $(this).html();
      var label = yearLabels[year]

      if (typeof(label) === 'undefined') {
        return
      }

      $(this).html(year + '<br/><small><i> ('+ label[lang] +')</i></small>');
    });
  };

  // Click
  $('.home-content .option-guide').click( function(e){
  	window.location = $('.home-content .option-guide .option-title').attr('href');
  });

  addYearSelectorCustomLabels();
});