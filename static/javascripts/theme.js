// Theme custom js methods
$(document).ready(function(){

  // Click
  $('.home-content .option-guide').click( function(e){
  	window.location = $('.home-content .option-guide .option-title').attr('href');
  });
});