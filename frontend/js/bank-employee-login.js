
// ========================================
// GIFT EMPLOYEE LOGIN
// ========================================

// Flask backend URL
const API_URL = "http://localhost:5000";


// Get HTML elements
const loginForm = document.getElementById("loginForm");

const identifierInput = document.getElementById("identifier");

const passwordInput = document.getElementById("password");

const loginButton = document.getElementById("loginButton");

const buttonText = document.getElementById("buttonText");

const loginMessage = document.getElementById("loginMessage");

const togglePassword = document.getElementById("togglePassword");


// ========================================
// SHOW / HIDE PASSWORD
// ========================================

togglePassword.addEventListener("click", function () {

    if (passwordInput.type === "password") {

        passwordInput.type = "text";

        togglePassword.textContent = "Hide";

        togglePassword.setAttribute(
            "aria-label",
            "Hide password"
        );

    } else {

        passwordInput.type = "password";

        togglePassword.textContent = "Show";

        togglePassword.setAttribute(
            "aria-label",
            "Show password"
        );

    }

});


// ========================================
// EMPLOYEE LOGIN
// ========================================

loginForm.addEventListener("submit", async function (event) {

    // Prevent normal form submission
    event.preventDefault();


    // Get entered values
    const username = identifierInput.value.trim();

    const password = passwordInput.value;


    // Validate input
    if (!username || !password) {

        loginMessage.textContent =
            "Please enter your username and password.";

        loginMessage.className = "login-message error";

        return;

    }


    // Disable button
    loginButton.disabled = true;

    buttonText.textContent = "Signing In...";

    loginMessage.textContent = "";

    loginMessage.className = "login-message";


    try {

        // Send login request to Flask
        const response = await fetch(
            `${API_URL}/api/employee/login`,
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    username: username,

                    password: password

                })

            }
        );


        // Convert response into JSON
        const data = await response.json();


        // Check login result
        if (!response.ok || !data.success) {

            throw new Error(
                data.message || "Invalid employee credentials."
            );

        }


        // Save employee information for this browser tab
        sessionStorage.setItem(
            "employee",
            JSON.stringify(data.employee)
        );


        // Display success message
        loginMessage.textContent =
            "Login successful! Redirecting...";

        loginMessage.className = "login-message success";


        // Redirect to employee dashboard
        window.location.href = "employee-dashboard.html";


    } catch (error) {

        console.error("Employee Login Error:", error);


        loginMessage.textContent =
            error.message || "Unable to connect to the server.";

        loginMessage.className = "login-message error";


        // Enable button again
        loginButton.disabled = false;

        buttonText.textContent = "Sign In";

    }

});
