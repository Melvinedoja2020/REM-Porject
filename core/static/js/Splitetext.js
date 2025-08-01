/*!
* SplitText 3.6.1
* https://greensock.com
*
* @license Copyright 2021, GreenSock. All rights reserved.
* Subject to the terms at https://greensock.com/standard-license or for Club GreenSock members, the agreement issued with that membership.
* @author: Jack Doyle, jack@greensock.com
*/
!function(D, u) {
    "object" == typeof exports && "undefined" != typeof module ? u(exports) : "function" == typeof define && define.amd ? define(["exports"], u) : u((D = D || self).window = D.window || {})
}(this, function(D) {
    "use strict";
    var _ = /([\uD800-\uDBFF][\uDC00-\uDFFF](?:[\u200D\uFE0F][\uD800-\uDBFF][\uDC00-\uDFFF]){2,}|\uD83D\uDC69(?:\u200D(?:(?:\uD83D\uDC69\u200D)?\uD83D\uDC67|(?:\uD83D\uDC69\u200D)?\uD83D\uDC66)|\uD83C[\uDFFB-\uDFFF])|\uD83D\uDC69\u200D(?:\uD83D\uDC69\u200D)?\uD83D\uDC66\u200D\uD83D\uDC66|\uD83D\uDC69\u200D(?:\uD83D\uDC69\u200D)?\uD83D\uDC67\u200D(?:\uD83D[\uDC66\uDC67])|\uD83C\uDFF3\uFE0F\u200D\uD83C\uDF08|(?:\uD83C[\uDFC3\uDFC4\uDFCA]|\uD83D[\uDC6E\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4-\uDEB6]|\uD83E[\uDD26\uDD37-\uDD39\uDD3D\uDD3E\uDDD6-\uDDDD])(?:\uD83C[\uDFFB-\uDFFF])\u200D[\u2640\u2642]\uFE0F|\uD83D\uDC69(?:\uD83C[\uDFFB-\uDFFF])\u200D(?:\uD83C[\uDF3E\uDF73\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92])|(?:\uD83C[\uDFC3\uDFC4\uDFCA]|\uD83D[\uDC6E\uDC6F\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4-\uDEB6]|\uD83E[\uDD26\uDD37-\uDD39\uDD3C-\uDD3E\uDDD6-\uDDDF])\u200D[\u2640\u2642]\uFE0F|\uD83C\uDDFD\uD83C\uDDF0|\uD83C\uDDF6\uD83C\uDDE6|\uD83C\uDDF4\uD83C\uDDF2|\uD83C\uDDE9(?:\uD83C[\uDDEA\uDDEC\uDDEF\uDDF0\uDDF2\uDDF4\uDDFF])|\uD83C\uDDF7(?:\uD83C[\uDDEA\uDDF4\uDDF8\uDDFA\uDDFC])|\uD83C\uDDE8(?:\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDEE\uDDF0-\uDDF5\uDDF7\uDDFA-\uDDFF])|(?:\u26F9|\uD83C[\uDFCB\uDFCC]|\uD83D\uDD75)(?:\uFE0F\u200D[\u2640\u2642]|(?:\uD83C[\uDFFB-\uDFFF])\u200D[\u2640\u2642])\uFE0F|(?:\uD83D\uDC41\uFE0F\u200D\uD83D\uDDE8|\uD83D\uDC69(?:\uD83C[\uDFFB-\uDFFF])\u200D[\u2695\u2696\u2708]|\uD83D\uDC69\u200D[\u2695\u2696\u2708]|\uD83D\uDC68(?:(?:\uD83C[\uDFFB-\uDFFF])\u200D[\u2695\u2696\u2708]|\u200D[\u2695\u2696\u2708]))\uFE0F|\uD83C\uDDF2(?:\uD83C[\uDDE6\uDDE8-\uDDED\uDDF0-\uDDFF])|\uD83D\uDC69\u200D(?:\uD83C[\uDF3E\uDF73\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\u2764\uFE0F\u200D(?:\uD83D\uDC8B\u200D(?:\uD83D[\uDC68\uDC69])|\uD83D[\uDC68\uDC69]))|\uD83C\uDDF1(?:\uD83C[\uDDE6-\uDDE8\uDDEE\uDDF0\uDDF7-\uDDFB\uDDFE])|\uD83C\uDDEF(?:\uD83C[\uDDEA\uDDF2\uDDF4\uDDF5])|\uD83C\uDDED(?:\uD83C[\uDDF0\uDDF2\uDDF3\uDDF7\uDDF9\uDDFA])|\uD83C\uDDEB(?:\uD83C[\uDDEE-\uDDF0\uDDF2\uDDF4\uDDF7])|[#\*0-9]\uFE0F\u20E3|\uD83C\uDDE7(?:\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEF\uDDF1-\uDDF4\uDDF6-\uDDF9\uDDFB\uDDFC\uDDFE\uDDFF])|\uD83C\uDDE6(?:\uD83C[\uDDE8-\uDDEC\uDDEE\uDDF1\uDDF2\uDDF4\uDDF6-\uDDFA\uDDFC\uDDFD\uDDFF])|\uD83C\uDDFF(?:\uD83C[\uDDE6\uDDF2\uDDFC])|\uD83C\uDDF5(?:\uD83C[\uDDE6\uDDEA-\uDDED\uDDF0-\uDDF3\uDDF7-\uDDF9\uDDFC\uDDFE])|\uD83C\uDDFB(?:\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDEE\uDDF3\uDDFA])|\uD83C\uDDF3(?:\uD83C[\uDDE6\uDDE8\uDDEA-\uDDEC\uDDEE\uDDF1\uDDF4\uDDF5\uDDF7\uDDFA\uDDFF])|\uD83C\uDFF4\uDB40\uDC67\uDB40\uDC62(?:\uDB40\uDC77\uDB40\uDC6C\uDB40\uDC73|\uDB40\uDC73\uDB40\uDC63\uDB40\uDC74|\uDB40\uDC65\uDB40\uDC6E\uDB40\uDC67)\uDB40\uDC7F|\uD83D\uDC68(?:\u200D(?:\u2764\uFE0F\u200D(?:\uD83D\uDC8B\u200D)?\uD83D\uDC68|(?:(?:\uD83D[\uDC68\uDC69])\u200D)?\uD83D\uDC66\u200D\uD83D\uDC66|(?:(?:\uD83D[\uDC68\uDC69])\u200D)?\uD83D\uDC67\u200D(?:\uD83D[\uDC66\uDC67])|\uD83C[\uDF3E\uDF73\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92])|(?:\uD83C[\uDFFB-\uDFFF])\u200D(?:\uD83C[\uDF3E\uDF73\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]))|\uD83C\uDDF8(?:\uD83C[\uDDE6-\uDDEA\uDDEC-\uDDF4\uDDF7-\uDDF9\uDDFB\uDDFD-\uDDFF])|\uD83C\uDDF0(?:\uD83C[\uDDEA\uDDEC-\uDDEE\uDDF2\uDDF3\uDDF5\uDDF7\uDDFC\uDDFE\uDDFF])|\uD83C\uDDFE(?:\uD83C[\uDDEA\uDDF9])|\uD83C\uDDEE(?:\uD83C[\uDDE8-\uDDEA\uDDF1-\uDDF4\uDDF6-\uDDF9])|\uD83C\uDDF9(?:\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDED\uDDEF-\uDDF4\uDDF7\uDDF9\uDDFB\uDDFC\uDDFF])|\uD83C\uDDEC(?:\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEE\uDDF1-\uDDF3\uDDF5-\uDDFA\uDDFC\uDDFE])|\uD83C\uDDFA(?:\uD83C[\uDDE6\uDDEC\uDDF2\uDDF3\uDDF8\uDDFE\uDDFF])|\uD83C\uDDEA(?:\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDED\uDDF7-\uDDFA])|\uD83C\uDDFC(?:\uD83C[\uDDEB\uDDF8])|(?:\u26F9|\uD83C[\uDFCB\uDFCC]|\uD83D\uDD75)(?:\uD83C[\uDFFB-\uDFFF])|(?:\uD83C[\uDFC3\uDFC4\uDFCA]|\uD83D[\uDC6E\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4-\uDEB6]|\uD83E[\uDD26\uDD37-\uDD39\uDD3D\uDD3E\uDDD6-\uDDDD])(?:\uD83C[\uDFFB-\uDFFF])|(?:[\u261D\u270A-\u270D]|\uD83C[\uDF85\uDFC2\uDFC7]|\uD83D[\uDC42\uDC43\uDC46-\uDC50\uDC66\uDC67\uDC70\uDC72\uDC74-\uDC76\uDC78\uDC7C\uDC83\uDC85\uDCAA\uDD74\uDD7A\uDD90\uDD95\uDD96\uDE4C\uDE4F\uDEC0\uDECC]|\uD83E[\uDD18-\uDD1C\uDD1E\uDD1F\uDD30-\uDD36\uDDD1-\uDDD5])(?:\uD83C[\uDFFB-\uDFFF])|\uD83D\uDC68(?:\u200D(?:(?:(?:\uD83D[\uDC68\uDC69])\u200D)?\uD83D\uDC67|(?:(?:\uD83D[\uDC68\uDC69])\u200D)?\uD83D\uDC66)|\uD83C[\uDFFB-\uDFFF])|(?:[\u261D\u26F9\u270A-\u270D]|\uD83C[\uDF85\uDFC2-\uDFC4\uDFC7\uDFCA-\uDFCC]|\uD83D[\uDC42\uDC43\uDC46-\uDC50\uDC66-\uDC69\uDC6E\uDC70-\uDC78\uDC7C\uDC81-\uDC83\uDC85-\uDC87\uDCAA\uDD74\uDD75\uDD7A\uDD90\uDD95\uDD96\uDE45-\uDE47\uDE4B-\uDE4F\uDEA3\uDEB4-\uDEB6\uDEC0\uDECC]|\uD83E[\uDD18-\uDD1C\uDD1E\uDD1F\uDD26\uDD30-\uDD39\uDD3D\uDD3E\uDDD1-\uDDDD])(?:\uD83C[\uDFFB-\uDFFF])?|(?:[\u231A\u231B\u23E9-\u23EC\u23F0\u23F3\u25FD\u25FE\u2614\u2615\u2648-\u2653\u267F\u2693\u26A1\u26AA\u26AB\u26BD\u26BE\u26C4\u26C5\u26CE\u26D4\u26EA\u26F2\u26F3\u26F5\u26FA\u26FD\u2705\u270A\u270B\u2728\u274C\u274E\u2753-\u2755\u2757\u2795-\u2797\u27B0\u27BF\u2B1B\u2B1C\u2B50\u2B55]|\uD83C[\uDC04\uDCCF\uDD8E\uDD91-\uDD9A\uDDE6-\uDDFF\uDE01\uDE1A\uDE2F\uDE32-\uDE36\uDE38-\uDE3A\uDE50\uDE51\uDF00-\uDF20\uDF2D-\uDF35\uDF37-\uDF7C\uDF7E-\uDF93\uDFA0-\uDFCA\uDFCF-\uDFD3\uDFE0-\uDFF0\uDFF4\uDFF8-\uDFFF]|\uD83D[\uDC00-\uDC3E\uDC40\uDC42-\uDCFC\uDCFF-\uDD3D\uDD4B-\uDD4E\uDD50-\uDD67\uDD7A\uDD95\uDD96\uDDA4\uDDFB-\uDE4F\uDE80-\uDEC5\uDECC\uDED0-\uDED2\uDEEB\uDEEC\uDEF4-\uDEF8]|\uD83E[\uDD10-\uDD3A\uDD3C-\uDD3E\uDD40-\uDD45\uDD47-\uDD4C\uDD50-\uDD6B\uDD80-\uDD97\uDDC0\uDDD0-\uDDE6])|(?:[#\*0-9\xA9\xAE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB-\u25FE\u2600-\u2604\u260E\u2611\u2614\u2615\u2618\u261D\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u2648-\u2653\u2660\u2663\u2665\u2666\u2668\u267B\u267F\u2692-\u2697\u2699\u269B\u269C\u26A0\u26A1\u26AA\u26AB\u26B0\u26B1\u26BD\u26BE\u26C4\u26C5\u26C8\u26CE\u26CF\u26D1\u26D3\u26D4\u26E9\u26EA\u26F0-\u26F5\u26F7-\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F\u2712\u2714\u2716\u271D\u2721\u2728\u2733\u2734\u2744\u2747\u274C\u274E\u2753-\u2755\u2757\u2763\u2764\u2795-\u2797\u27A1\u27B0\u27BF\u2934\u2935\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55\u3030\u303D\u3297\u3299]|\uD83C[\uDC04\uDCCF\uDD70\uDD71\uDD7E\uDD7F\uDD8E\uDD91-\uDD9A\uDDE6-\uDDFF\uDE01\uDE02\uDE1A\uDE2F\uDE32-\uDE3A\uDE50\uDE51\uDF00-\uDF21\uDF24-\uDF93\uDF96\uDF97\uDF99-\uDF9B\uDF9E-\uDFF0\uDFF3-\uDFF5\uDFF7-\uDFFF]|\uD83D[\uDC00-\uDCFD\uDCFF-\uDD3D\uDD49-\uDD4E\uDD50-\uDD67\uDD6F\uDD70\uDD73-\uDD7A\uDD87\uDD8A-\uDD8D\uDD90\uDD95\uDD96\uDDA4\uDDA5\uDDA8\uDDB1\uDDB2\uDDBC\uDDC2-\uDDC4\uDDD1-\uDDD3\uDDDC-\uDDDE\uDDE1\uDDE3\uDDE8\uDDEF\uDDF3\uDDFA-\uDE4F\uDE80-\uDEC5\uDECB-\uDED2\uDEE0-\uDEE5\uDEE9\uDEEB\uDEEC\uDEF0\uDEF3-\uDEF8]|\uD83E[\uDD10-\uDD3A\uDD3C-\uDD3E\uDD40-\uDD45\uDD47-\uDD4C\uDD50-\uDD6B\uDD80-\uDD97\uDDC0\uDDD0-\uDDE6])\uFE0F)/;
    function k(D) {
        return e.getComputedStyle(D)
    }
    function n(D, u) {
        var e;
        return i(D) ? D : "string" == (e = typeof D) && !u && D ? E.call(X.querySelectorAll(D), 0) : D && "object" == e && "length"in D ? E.call(D, 0) : D ? [D] : []
    }
    function o(D) {
        return "absolute" === D.position || !0 === D.absolute
    }
    function p(D, u) {
        for (var e, t = u.length; -1 < --t; )
            if (e = u[t],
            D.substr(0, e.length) === e)
                return e.length
    }
    function r(D, u) {
        void 0 === D && (D = "");
        var e = ~D.indexOf("++")
          , t = 1;
        return e && (D = D.split("++").join("")),
        function() {
            return "<" + u + " style='position:relative;display:inline-block;'" + (D ? " class='" + D + (e ? t++ : "") + "'>" : ">")
        }
    }
    function s(D, u, e) {
        var t = D.nodeType;
        if (1 === t || 9 === t || 11 === t)
            for (D = D.firstChild; D; D = D.nextSibling)
                s(D, u, e);
        else
            3 !== t && 4 !== t || (D.nodeValue = D.nodeValue.split(u).join(e))
    }
    function t(D, u) {
        for (var e = u.length; -1 < --e; )
            D.push(u[e])
    }
    function u(D, u, e) {
        for (var t; D && D !== u; ) {
            if (t = D._next || D.nextSibling)
                return t.textContent.charAt(0) === e;
            D = D.parentNode || D._parent
        }
    }
    function v(D) {
        var u, e, t = n(D.childNodes), F = t.length;
        for (u = 0; u < F; u++)
            (e = t[u])._isSplit ? v(e) : u && e.previousSibling && 3 === e.previousSibling.nodeType ? (e.previousSibling.nodeValue += 3 === e.nodeType ? e.nodeValue : e.firstChild.nodeValue,
            D.removeChild(e)) : 3 !== e.nodeType && (D.insertBefore(e.firstChild, e),
            D.removeChild(e))
    }
    function w(D, u) {
        return parseFloat(u[D]) || 0
    }
    function x(D, e, F, C, i, n, E) {
        var r, l, p, d, a, h, B, f, A, c, x, g, y = k(D), _ = w("paddingLeft", y), b = -999, S = w("borderBottomWidth", y) + w("borderTopWidth", y), T = w("borderLeftWidth", y) + w("borderRightWidth", y), m = w("paddingTop", y) + w("paddingBottom", y), N = w("paddingLeft", y) + w("paddingRight", y), L = w("fontSize", y) * (e.lineThreshold || .2), W = y.textAlign, H = [], O = [], V = [], j = e.wordDelimiter || " ", M = e.tag ? e.tag : e.span ? "span" : "div", R = e.type || e.split || "chars,words,lines", z = i && ~R.indexOf("lines") ? [] : null, P = ~R.indexOf("words"), q = ~R.indexOf("chars"), G = o(e), I = e.linesClass, J = ~(I || "").indexOf("++"), K = [], Q = "flex" === y.display, U = D.style.display;
        for (J && (I = I.split("++").join("")),
        Q && (D.style.display = "block"),
        p = (l = D.getElementsByTagName("*")).length,
        a = [],
        r = 0; r < p; r++)
            a[r] = l[r];
        if (z || G)
            for (r = 0; r < p; r++)
                ((h = (d = a[r]).parentNode === D) || G || q && !P) && (g = d.offsetTop,
                z && h && Math.abs(g - b) > L && ("BR" !== d.nodeName || 0 === r) && (B = [],
                z.push(B),
                b = g),
                G && (d._x = d.offsetLeft,
                d._y = g,
                d._w = d.offsetWidth,
                d._h = d.offsetHeight),
                z && ((d._isSplit && h || !q && h || P && h || !P && d.parentNode.parentNode === D && !d.parentNode._isSplit) && (B.push(d),
                d._x -= _,
                u(d, D, j) && (d._wordEnd = !0)),
                "BR" === d.nodeName && (d.nextSibling && "BR" === d.nextSibling.nodeName || 0 === r) && z.push([])));
        for (r = 0; r < p; r++)
            if (h = (d = a[r]).parentNode === D,
            "BR" !== d.nodeName)
                if (G && (A = d.style,
                P || h || (d._x += d.parentNode._x,
                d._y += d.parentNode._y),
                A.left = d._x + "px",
                A.top = d._y + "px",
                A.position = "absolute",
                A.display = "block",
                A.width = d._w + 1 + "px",
                A.height = d._h + "px"),
                !P && q)
                    if (d._isSplit)
                        for (d._next = l = d.nextSibling,
                        d.parentNode.appendChild(d); l && 3 === l.nodeType && " " === l.textContent; )
                            d._next = l.nextSibling,
                            d.parentNode.appendChild(l),
                            l = l.nextSibling;
                    else
                        d.parentNode._isSplit ? (d._parent = d.parentNode,
                        !d.previousSibling && d.firstChild && (d.firstChild._isFirst = !0),
                        d.nextSibling && " " === d.nextSibling.textContent && !d.nextSibling.nextSibling && K.push(d.nextSibling),
                        d._next = d.nextSibling && d.nextSibling._isFirst ? null : d.nextSibling,
                        d.parentNode.removeChild(d),
                        a.splice(r--, 1),
                        p--) : h || (g = !d.nextSibling && u(d.parentNode, D, j),
                        d.parentNode._parent && d.parentNode._parent.appendChild(d),
                        g && d.parentNode.appendChild(X.createTextNode(" ")),
                        "span" === M && (d.style.display = "inline"),
                        H.push(d));
                else
                    d.parentNode._isSplit && !d._isSplit && "" !== d.innerHTML ? O.push(d) : q && !d._isSplit && ("span" === M && (d.style.display = "inline"),
                    H.push(d));
            else
                z || G ? (d.parentNode && d.parentNode.removeChild(d),
                a.splice(r--, 1),
                p--) : P || D.appendChild(d);
        for (r = K.length; -1 < --r; )
            K[r].parentNode.removeChild(K[r]);
        if (z) {
            for (G && (c = X.createElement(M),
            D.appendChild(c),
            x = c.offsetWidth + "px",
            g = c.offsetParent === D ? 0 : D.offsetLeft,
            D.removeChild(c)),
            A = D.style.cssText,
            D.style.cssText = "display:none;"; D.firstChild; )
                D.removeChild(D.firstChild);
            for (f = " " === j && (!G || !P && !q),
            r = 0; r < z.length; r++) {
                for (B = z[r],
                (c = X.createElement(M)).style.cssText = "display:block;text-align:" + W + ";position:" + (G ? "absolute;" : "relative;"),
                I && (c.className = I + (J ? r + 1 : "")),
                V.push(c),
                p = B.length,
                l = 0; l < p; l++)
                    "BR" !== B[l].nodeName && (d = B[l],
                    c.appendChild(d),
                    f && d._wordEnd && c.appendChild(X.createTextNode(" ")),
                    G && (0 === l && (c.style.top = d._y + "px",
                    c.style.left = _ + g + "px"),
                    d.style.top = "0px",
                    g && (d.style.left = d._x - g + "px")));
                0 === p ? c.innerHTML = "&nbsp;" : P || q || (v(c),
                s(c, String.fromCharCode(160), " ")),
                G && (c.style.width = x,
                c.style.height = d._h + "px"),
                D.appendChild(c)
            }
            D.style.cssText = A
        }
        G && (E > D.clientHeight && (D.style.height = E - m + "px",
        D.clientHeight < E && (D.style.height = E + S + "px")),
        n > D.clientWidth && (D.style.width = n - N + "px",
        D.clientWidth < n && (D.style.width = n + T + "px"))),
        Q && (U ? D.style.display = U : D.style.removeProperty("display")),
        t(F, H),
        P && t(C, O),
        t(i, V)
    }
    function y(D, u, e, t) {
        var F, C, i, n, E, r, l, d, a = u.tag ? u.tag : u.span ? "span" : "div", h = ~(u.type || u.split || "chars,words,lines").indexOf("chars"), B = o(u), f = u.wordDelimiter || " ", A = " " !== f ? "" : B ? "&#173; " : " ", c = "</" + a + ">", x = 1, g = u.specialChars ? "function" == typeof u.specialChars ? u.specialChars : p : null, y = X.createElement("div"), v = D.parentNode;
        for (v.insertBefore(y, D),
        y.textContent = D.nodeValue,
        v.removeChild(D),
        l = -1 !== (F = function getText(D) {
            var u = D.nodeType
              , e = "";
            if (1 === u || 9 === u || 11 === u) {
                if ("string" == typeof D.textContent)
                    return D.textContent;
                for (D = D.firstChild; D; D = D.nextSibling)
                    e += getText(D)
            } else if (3 === u || 4 === u)
                return D.nodeValue;
            return e
        }(D = y)).indexOf("<"),
        !1 !== u.reduceWhiteSpace && (F = F.replace(S, " ").replace(b, "")),
        l && (F = F.split("<").join("{{LT}}")),
        E = F.length,
        C = (" " === F.charAt(0) ? A : "") + e(),
        i = 0; i < E; i++)
            if (r = F.charAt(i),
            g && (d = g(F.substr(i), u.specialChars)))
                r = F.substr(i, d || 1),
                C += h && " " !== r ? t() + r + "</" + a + ">" : r,
                i += d - 1;
            else if (r === f && F.charAt(i - 1) !== f && i) {
                for (C += x ? c : "",
                x = 0; F.charAt(i + 1) === f; )
                    C += A,
                    i++;
                i === E - 1 ? C += A : ")" !== F.charAt(i + 1) && (C += A + e(),
                x = 1)
            } else
                "{" === r && "{{LT}}" === F.substr(i, 6) ? (C += h ? t() + "{{LT}}</" + a + ">" : "{{LT}}",
                i += 5) : 55296 <= r.charCodeAt(0) && r.charCodeAt(0) <= 56319 || 65024 <= F.charCodeAt(i + 1) && F.charCodeAt(i + 1) <= 65039 ? (n = ((F.substr(i, 12).split(_) || [])[1] || "").length || 2,
                C += h && " " !== r ? t() + F.substr(i, n) + "</" + a + ">" : F.substr(i, n),
                i += n - 1) : C += h && " " !== r ? t() + r + "</" + a + ">" : r;
        D.outerHTML = C + (x ? c : ""),
        l && s(v, "{{LT}}", "<")
    }
    function z(D, u, e, t) {
        var F, C, i = n(D.childNodes), E = i.length, s = o(u);
        if (3 !== D.nodeType || 1 < E) {
            for (u.absolute = !1,
            F = 0; F < E; F++)
                (C = i[F])._next = C._isFirst = C._parent = C._wordEnd = null,
                3 === C.nodeType && !/\S+/.test(C.nodeValue) || (s && 3 !== C.nodeType && "inline" === k(C).display && (C.style.display = "inline-block",
                C.style.position = "relative"),
                C._isSplit = !0,
                z(C, u, e, t));
            return u.absolute = s,
            void (D._isSplit = !0)
        }
        y(D, u, e, t)
    }
    var X, e, F, C, b = /(?:\r|\n|\t\t)/g, S = /(?:\s\s+)/g, i = Array.isArray, E = [].slice, l = ((C = SplitText.prototype).split = function split(D) {
        this.isSplit && this.revert(),
        this.vars = D = D || this.vars,
        this._originals.length = this.chars.length = this.words.length = this.lines.length = 0;
        for (var u, e, t, F = this.elements.length, C = D.tag ? D.tag : D.span ? "span" : "div", i = r(D.wordsClass, C), n = r(D.charsClass, C); -1 < --F; )
            t = this.elements[F],
            this._originals[F] = t.innerHTML,
            u = t.clientHeight,
            e = t.clientWidth,
            z(t, D, i, n),
            x(t, D, this.chars, this.words, this.lines, e, u);
        return this.chars.reverse(),
        this.words.reverse(),
        this.lines.reverse(),
        this.isSplit = !0,
        this
    }
    ,
    C.revert = function revert() {
        var e = this._originals;
        if (!e)
            throw "revert() call wasn't scoped properly.";
        return this.elements.forEach(function(D, u) {
            return D.innerHTML = e[u]
        }),
        this.chars = [],
        this.words = [],
        this.lines = [],
        this.isSplit = !1,
        this
    }
    ,
    SplitText.create = function create(D, u) {
        return new SplitText(D,u)
    }
    ,
    SplitText);
    function SplitText(D, u) {
        F || function _initCore() {
            X = document,
            e = window,
            F = 1
        }(),
        this.elements = n(D),
        this.chars = [],
        this.words = [],
        this.lines = [],
        this._originals = [],
        this.vars = u || {},
        this.split(u)
    }
    l.version = "3.6.1",
    D.SplitText = l,
    D.default = l;
    if (typeof (window) === "undefined" || window !== D) {
        Object.defineProperty(D, "__esModule", {
            value: !0
        })
    } else {
        delete D.default
    }
});
;
