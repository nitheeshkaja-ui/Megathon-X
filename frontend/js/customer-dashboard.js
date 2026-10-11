
const API_URL = "http://127.0.0.1:5000";

// Get logged-in customer information
const loggedInUser = JSON.parse(
    localStorage.getItem("gciCustomerUser") || "null"
);

const loadingMessage = document.getElementById("loadingMessage");
const errorMessage = document.getElementById("errorMessage");
const dashboardContent = document.getElementById("dashboardContent");

// Display text safely
function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent =
            value === null || value === undefined || value === ""
                ? "Not provided"
                : value;
    }
}

// Convert database preference values into readable text
function yesNo(value) {
    return Number(value) === 1 ? "Yes" : "No";
}

// Load customer dashboard
async function loadCustomerDashboard() {

    if (!loggedInUser || !loggedInUser.user_id) {
        window.location.href = "customer-login.html";
        return;
    }

    try {
        const response = await fetch(
            `${API_URL}/api/customer/dashboard/${loggedInUser.user_id}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to load customer details."
            );
        }

        const customer = data.customer;

        // Header
        setText("customerName", customer.full_name);

        const initial = customer.full_name
            ? customer.full_name.charAt(0).toUpperCase()
            : "C";

        setText("profileInitial", initial);

        // Profile details
        setText("fullName", customer.full_name);
        setText("customerRef", customer.customer_ref);
        setText("email", customer.email);
        setText("phone", customer.phone_number);
        setText("city", customer.city);

        setText("homeOwner", yesNo(customer.home_owner));
        setText("solarInterest", yesNo(customer.solar_interest));
        setText("paperStatement", yesNo(customer.paper_statement));

        // Digital banking
        setText(
            "digitalStatus",
            Number(customer.digital_banking) === 1
                ? "Active"
                : "Inactive"
        );

        // Show dashboard
        loadingMessage.classList.add("hidden");
        errorMessage.classList.add("hidden");
        dashboardContent.classList.remove("hidden");

    } catch (error) {

        console.error("Dashboard error:", error);

        loadingMessage.classList.add("hidden");
        errorMessage.textContent = error.message;
        errorMessage.classList.remove("hidden");
    }
}

// Logout
document.getElementById("logoutButton").addEventListener(
    "click",
    function () {
        localStorage.removeItem("gciCustomerUser");
        window.location.href = "customer-login.html";
    }
);

// Opportunity buttons (detailed pages will be built later)
document.querySelectorAll(".learn-button").forEach(button => {

    button.addEventListener("click", function () {

        const opportunity = this.dataset.opportunity;

        alert(
            opportunity +
            " details and calculator will be available in the next development stage."
        );
    });

});

// Load dashboard when page opens
loadCustomerDashboard();
