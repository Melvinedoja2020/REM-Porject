function isElementInViewport($el) {
    var top = $el.offset().top;
    var bottom = top + $el.outerHeight();
    var viewportTop = $(window).scrollTop();
    var viewportBottom = viewportTop + $(window).height();
    return bottom > viewportTop && top < viewportBottom;
}

if ($(".counter-scroll").length > 0) {

    $(window).on("scroll", function () {
        if ($(".odometer").length > 0) {
            if (isElementInViewport($(".odometer"))) {
                setTimeout(function () {
                    $(".style-1-1").html(26);
                    $(".style-1-2").html(4130);
                    $(".style-1-3").html(98);
                    $(".style-1-4").html(1780);
                }, 0);
            }
        }
        if ($(".odometer.style-2").length > 0) {
            if (isElementInViewport($(".odometer.style-2"))) {
                setTimeout(function () {
                    $(".style-2-1").html(900);
                    $(".style-2-2").html(287);
                    $(".style-2-3").html(3);
                }, 0);
            }
        }
        if ($(".odometer.style-3").length > 0) {
            if (isElementInViewport($(".odometer.style-3"))) {
                setTimeout(function () {
                    $(".style-3-1").html(250);
                    $(".style-3-2").html(470);
                }, 0);
            }
        }
        if ($(".odometer.style-4").length > 0) {
            if (isElementInViewport($(".odometer.style-4"))) {
                setTimeout(function () {
                    $(".style-4-1").html(950);
                    $(".style-4-2").html(2);
                    $(".style-4-3").html(470);
                    $(".style-4-4").html(2);
                }, 0);
            }
        }
        if ($(".odometer.style-5").length > 0) {
            if (isElementInViewport($(".odometer.style-5"))) {
                setTimeout(function () {
                    $(".style-5-1").html(2);
                }, 0);
            }
        }
    });
}
