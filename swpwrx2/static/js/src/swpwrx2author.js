function Swpwrx2Author(runtime, element, questions) {
    var qu1 = $( "#variant1", element );
    var dm1 = $( ".display_math", qu1 );

    console.info('Swpwrx2Author questions',questions);

    switch (questions) {
        case 1:
            qu1.removeClass("problem-empty");
            break;
    }

    if( dm1.html()=="\\(\\)" ){
        dm1.addClass("problem-empty");
    }else{
        dm1.removeClass("problem-empty");
    }

    /* PAGE LOAD EVENT */
    $(function ($) {
        MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
        setTimeout(function () {
            console.info(questions)
        }, 250);
    });
}
