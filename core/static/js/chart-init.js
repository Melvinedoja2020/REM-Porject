var ctx = document.getElementById("lineChart").getContext("2d");
var gradient = ctx.createLinearGradient(0, 0, 0, 400);

gradient.addColorStop(0, "rgba(21, 99, 223,0.2)");
gradient.addColorStop(1, "rgba(21, 99, 223,0)");

var myChart = new Chart(ctx, {
    type: "line",
    data: {
        labels: [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        datasets: [
            {
                data: [
                    42, 45, 70, 65, 140, 130, 145, 145, 160, 135, 140, 130, 135,
                    140, 250,
                ],
                backgroundColor: gradient,
                borderColor: "#f1913d",
                borderWidth: 2,
                fill: true,
                tension: 0.4,
            },
        ],
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                display: false,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
            },
        },
    },
});
