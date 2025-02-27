document.addEventListener("DOMContentLoaded", function() {
    console.log("Dashboard Loaded");

    // Fetch data from the API
    fetch("/api/data")
        .then(response => response.json())
        .then(data => {
            // Add new data dynamically to the dashboard
            addServerData(data);
        });

    // Function to dynamically add new server data boxes
    function addServerData(data) {
        const statusOverview = document.getElementById("status-overview");

        data.labels.forEach((label, index) => {
            const newStatusBox = document.createElement("div");
            newStatusBox.classList.add("status-box");

            // Apply dynamic class based on some logic (just an example, you can customize this)
            if (index % 2 === 0) {
                newStatusBox.classList.add("green");
            } else {
                newStatusBox.classList.add("red");
            }

            newStatusBox.innerHTML = `${label}<br>Databases: ${data.values[index]}<br>Status: Online`;
            statusOverview.appendChild(newStatusBox);
        });
    }

    // Table row color change on alert levels (if any)
    document.querySelectorAll("td.red").forEach(cell => {
        cell.parentElement.style.backgroundColor = "#ffe6e6";
    });
    document.querySelectorAll("td.yellow").forEach(cell => {
        cell.parentElement.style.backgroundColor = "#fff5cc";
    });
});
