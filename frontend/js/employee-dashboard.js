
const API_URL = "http://localhost:5000";

// =====================================
// CHECK EMPLOYEE LOGIN
// =====================================

const employeeData = sessionStorage.getItem("employee");

if (!employeeData) {
    window.location.replace("bank-employee-login.html");
} else {
    startDashboard();
}


// =====================================
// START DASHBOARD
// =====================================

function startDashboard() {

    const employee = JSON.parse(employeeData);

    // HTML ELEMENTS
    const totalCustomers = document.getElementById("totalCustomers");
    const totalProducts = document.getElementById("totalProducts");
    const totalRecommendations = document.getElementById("totalRecommendations");
    const recommendationsBody = document.getElementById("recommendationsBody");


    // =====================================
    // DISPLAY EMPLOYEE DETAILS
    // =====================================

    document.getElementById("welcomeHeading").textContent =
        "Welcome, " + (employee.full_name || employee.name || "Employee");

    document.getElementById("bankName").textContent =
        employee.bank_name || "Bank";

    document.getElementById("branchName").textContent =
        employee.branch_name || "Branch";

    document.getElementById("employeeBadge").textContent =
        employee.role || "Bank Officer";

    document.getElementById("sidebarEmployeeName").textContent =
        employee.full_name || employee.name || employee.username || "Employee";

    document.getElementById("sidebarEmployeeRole").textContent =
        employee.role || "Bank Officer";


    // =====================================
    // LOGOUT
    // =====================================

    document.getElementById("logoutButton").addEventListener("click", function () {

        sessionStorage.removeItem("employee");

        window.location.replace("bank-employee-login.html");

    });


    // =====================================
    // LOAD DASHBOARD STATISTICS
    // =====================================

    async function loadDashboard() {

        try {

            const response = await fetch(
                API_URL + "/api/employee/dashboard/" + employee.user_id
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Unable to load dashboard.");
            }

            const stats = data.dashboard || data;

            totalCustomers.textContent =
                stats.total_customers ?? 0;

            totalProducts.textContent =
                stats.total_green_products ?? 0;

            totalRecommendations.textContent =
                stats.total_recommendations ?? 0;

        } catch (error) {

            console.error("Dashboard Error:", error);

            totalCustomers.textContent = "Error";
            totalProducts.textContent = "Error";
            totalRecommendations.textContent = "Error";

        }

    }


    // =====================================
    // LOAD CUSTOMER RECOMMENDATIONS
    // =====================================

    async function loadRecommendations() {

        recommendationsBody.replaceChildren();

        showTableMessage("Loading recommendations...", "loading-message");

        try {

            const response = await fetch(
                API_URL + "/api/employee/recommendations/" + employee.user_id
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Unable to load recommendations.");
            }

            const recommendations = Array.isArray(data.recommendations)
                ? data.recommendations
                : Array.isArray(data.data)
                    ? data.data
                    : [];

            recommendationsBody.replaceChildren();

            if (recommendations.length === 0) {

                showTableMessage("No recommendations found.", "empty-message");

                return;
            }


            // CREATE TABLE ROWS

            recommendations.forEach(function (item) {

                const row = document.createElement("tr");


                // CUSTOMER

                const customerCell = document.createElement("td");

                const customerName = document.createElement("div");

                customerName.className = "customer-name";

                customerName.textContent =
                    item.customer_name || "Unknown Customer";


                const customerRef = document.createElement("div");

                customerRef.className = "customer-ref";

                customerRef.textContent =
                    item.customer_ref || "No reference";

                customerCell.append(customerName, customerRef);


                // GREEN PRODUCT

                const productCell = document.createElement("td");

                productCell.className = "product-name";

                productCell.textContent =
                    item.product_name || item.name || "Green Product";


                // EXPLANATION

                const explanationCell = document.createElement("td");

                explanationCell.textContent =
                    item.ai_explanation ||
                    "This opportunity was identified by the recommendation rules.";


                // ELIGIBILITY

                const eligibilityCell = document.createElement("td");

                const eligibilityBadge = document.createElement("span");

                eligibilityBadge.className = "status-pill";

                eligibilityBadge.textContent = "Needs verification";

                eligibilityCell.appendChild(eligibilityBadge);


                // RECOMMENDATION STATUS

                const statusCell = document.createElement("td");

                const statusBadge = document.createElement("span");

                statusBadge.className = "status-pill";

                statusBadge.textContent =
                    item.recommendation_status || "Recommended";

                statusCell.appendChild(statusBadge);


                // ADD ROW

                row.append(
                    customerCell,
                    productCell,
                    explanationCell,
                    eligibilityCell,
                    statusCell
                );

                recommendationsBody.appendChild(row);

            });

        } catch (error) {

            console.error("Recommendation Error:", error);

            showTableMessage(
                error.message || "Unable to load recommendations.",
                "error-message"
            );

        }

    }


    // =====================================
    // TABLE MESSAGE HELPER
    // =====================================

    function showTableMessage(message, className) {

        recommendationsBody.replaceChildren();

        const row = document.createElement("tr");

        const cell = document.createElement("td");

        cell.colSpan = 5;

        cell.className = className;

        cell.textContent = message;

        row.appendChild(cell);

        recommendationsBody.appendChild(row);

    }


    // =====================================
    // RUN DASHBOARD
    // =====================================

    loadDashboard();

    loadRecommendations();

}
