
const API_BASE = "http://127.0.0.1:5000/api";

const loginForm = document.getElementById("loginForm");
const identifierInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const loginButton = document.getElementById("loginButton");
const buttonText = document.getElementById("buttonText");
const loginMessage = document.getElementById("loginMessage");
const togglePassword = document.getElementById("togglePassword");

function showMessage(message, type = "error") {
    loginMessage.textContent = message;
    loginMessage.classList.remove("is-error", "is-success");

    if (message) {
        loginMessage.classList.add(
            type === "success" ? "is-success" : "is-error"
        );
    }
}

// Show or hide the password.
if (togglePassword) {
    togglePassword.addEventListener("click", () => {
        const shouldShow = passwordInput.type === "password";

        passwordInput.type = shouldShow ? "text" : "password";
        togglePassword.textContent = shouldShow ? "Hide" : "Show";
        togglePassword.setAttribute(
            "aria-label",
            shouldShow ? "Hide password" : "Show password"
        );
    });
}

// Verify the entered credentials through the Flask API.
loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const identifier = identifierInput.value.trim();
    const password = passwordInput.value;

    if (!identifier || !password) {
        showMessage("Please enter your email or phone number and password.");
        return;
    }

    loginButton.disabled = true;

    if (buttonText) {
        buttonText.textContent = "Signing in...";
    }

    showMessage("");

    try {
        const isEmail = identifier.includes("@");

        const loginData = {
            password: password
        };

        // Send the identifier using the appropriate API field.
        if (isEmail) {
            loginData.email = identifier;
        } else {
            loginData.phone_number = identifier;
        }

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(loginData)
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            showMessage(
                result.message || "Invalid credentials. Please try again."
            );
            return;
        }

        const customer = result.user;

        // Accept only a valid customer account returned by the backend.
        if (
            !customer ||
            !customer.user_id ||
            customer.role !== "Customer"
        ) {
            showMessage(
                "The server did not return a valid customer account."
            );
            return;
        }

        // Store customer details for the dashboard.
        // Never store the password.
        sessionStorage.setItem("customer", JSON.stringify(customer));
        sessionStorage.setItem("giftCustomer", JSON.stringify(customer));

        showMessage("Login successful. Opening your dashboard...", "success");

        // Redirect only after the backend confirms successful login.
        window.location.href = "customer-dashboard.html";

    } catch (error) {
        console.error("Customer login error:", error);

        showMessage(
            "Cannot connect to the backend. Please start Flask and try again."
        );
    } finally {
        loginButton.disabled = false;

        if (buttonText) {
            buttonText.textContent = "Sign In";
        }
    }
});
