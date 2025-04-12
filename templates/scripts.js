document.addEventListener('DOMContentLoaded', function() {
    // Example of handling form submission for login
    const loginForm = document.querySelector('form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            // Handle login logic here
            const username = loginForm.username.value;
            const password = loginForm.password.value;

            // You can add AJAX call here to submit the form data
            console.log('Logging in with:', username, password);
        });
    }

    // Example of rendering a pie chart
    const ctx = document.getElementById('myPieChart');
    if (ctx) {
        const myPieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Category 1', 'Category 2', 'Category 3'], // Replace with actual categories
                datasets: [{
                    label: 'Ticket Categories',
                    data: [12, 19, 3], // Replace with actual data
                    backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56'],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    }
});