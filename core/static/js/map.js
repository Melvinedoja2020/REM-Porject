(function ($) {
    "use strict";

    mapboxgl.accessToken =
        "pk.eyJ1IjoiaG9hbmdoYW5kbiIsImEiOiJjbTdsbTkydm8wZGpiMmxxcTdvdzVqbHd3In0.HUUli-jvI1ALTBuzSeKTpw";

    const locations = [
        {
            coordinates: [-73.994601, 40.711536],
            properties: {
                image: "images/section/box-house.jpg",
                url: "property-details-v1.html",
                title: "Elegant studio flat",
                location: "102 Ingraham St, Brooklyn...",
                price: "$8.600",
                beds: 3,
                baths: 2,
                sqft: "2,100",
            },
        },
        {
            coordinates: [-74.016245, 40.710885],
            properties: {
                image: "images/section/box-house-2.jpg",
                url: "property-details-v1.html",
                title: "Elegant studio flat",
                location: "102 Ingraham St, Brooklyn...",
                price: "$8.600",
                beds: 3,
                baths: 2,
                sqft: "2,100",
            },
        },
        {
            coordinates: [-74.010316, 40.715504],
            properties: {
                image: "images/section/box-house-3.jpg",
                url: "property-details-v1.html",
                title: "Elegant studio flat",
                location: "102 Ingraham St, Brooklyn...",
                price: "$8.600",
                beds: 3,
                baths: 2,
                sqft: "2,100",
            },
        },
        {
            coordinates: [-74.010316, 40.726204],
            properties: {
                image: "images/section/box-house-4.jpg",
                url: "property-details-v1.html",
                title: "Elegant studio flat",
                location: "102 Ingraham St, Brooklyn...",
                price: "$8.600",
                beds: 3,
                baths: 2,
                sqft: "2,100",
            },
        },
    ];

    const map = new mapboxgl.Map({
        container: "map",
        style: "mapbox://styles/mapbox/light-v11",
        center: [-74.003099, 40.709295],
        zoom: 13,
        cooperativeGestures: true
    });

    // Add navigation controls
    map.addControl(new mapboxgl.NavigationControl(), "top-left");

    // Add geolocate control
    map.addControl(
        new mapboxgl.GeolocateControl({
            positionOptions: {
                enableHighAccuracy: true,
            },
            trackUserLocation: true,
            showUserHeading: true,
        }),
        "top-left"
    );

    // Create popup
    const popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: [0, -15],
        className: "property-popup",

    });

    // Add markers and popups
    locations.forEach((location, index) => {
        // Create marker element
        const el = document.createElement("div");
        el.className = "map-marker-container";
        el.innerHTML = `
            <div class="marker-container">
                <div class="marker-card">
                    <div class=" face"></div>
                </div>
            </div>
        `;

        // Create popup content
        const popupContent = `
        <div class="map-listing-item">
    <div class="box-house">
        <div class="infoBox-close"><i class="icon icon-close"></i></div>
        <div class="image-wrap">
            <a href="#">
                <img src="${location.properties.image}" alt="${location.properties.image}">
            </a>
            <ul class="box-tag flex gap-8">
                <li class="flat-tag text-4 bg-main fw-6 text-white">For Sale</li>
            </ul>
            <div class="list-btn flex gap-8">
                <a href="#" class="btn-icon save"><i class="icon-save"></i></a>
                <a href="#" class="btn-icon find"><i class="icon-find-plus"></i></a>
            </div>
        </div>
        <div class="content">
            <h5 class="title"><a href="${location.properties.url}">${location.properties.title}</a></h5>
            <p class="location text-1 flex items-center gap-8">
                <i class="icon-location"></i>  ${location.properties.location}
            </p>
            <ul class="meta-list flex">
                <li class="text-1 flex"><span>${location.properties.beds}</span>Beds</li>
                <li class="text-1 flex"><span>${location.properties.baths}</span>Baths</li>
                <li class="text-1 flex"><span>${location.properties.sqft}</span>Sqft</li>
            </ul>
            <div class="bot flex justify-between items-center">
                <h5 class="price">${location.properties.price}</h5>
                <div class="wrap-btn flex">
                    <a href="#" class="tf-btn style-border pd-4">Details</a>
                </div>
            </div>
        </div>
    </div>
        </div>

        `;

        // Add marker
        const marker = new mapboxgl.Marker(el)
            .setLngLat(location.coordinates)
            .addTo(map);

        // Add hover events
        el.addEventListener("click", () => {
            const markerContainer = el.querySelector(".marker-container");
            if (markerContainer.classList.contains("clicked")) {
                markerContainer.classList.remove("clicked");

                popup.remove();
            } else {
                markerContainer.classList.add("clicked");
                popup
                    .setLngLat(location.coordinates)
                    .setHTML(popupContent)
                    .addTo(map);
                 // Add event listener for closing the popup
                 const closeButton = popup.getElement().querySelector(".infoBox-close");
                 closeButton.addEventListener("click", () => {
                     markerContainer.classList.remove("clicked");
                     popup.remove();
                 });
            }

        });
    });

    // Disable map rotation
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
})(this.jQuery);
