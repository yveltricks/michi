// Create this file at "app/static/js/workout-timer.js"

let startTime = Date.now();
let elapsedTime = 0;
let timerInterval = null;
let isPaused = false;
let resetConfirmationActive = false;
let resetTimeout = null;

// Start the timer immediately when the page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('workout-timer')) {
        startTimer();
    }
});

function startTimer() {
    startTime = Date.now() - elapsedTime;
    timerInterval = setInterval(updateTimer, 1000);
    isPaused = false;
    
    const pauseTimerButton = document.getElementById('pause-timer');
    if (pauseTimerButton) {
        pauseTimerButton.textContent = 'Pause Timer';
    }
}

function updateTimer() {
    if (!isPaused) {
        elapsedTime = Date.now() - startTime;
        displayTime(elapsedTime);
    }
}

function displayTime(time) {
    const hours = Math.floor(time / (1000 * 60 * 60));
    const minutes = Math.floor((time % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((time % (1000 * 60)) / 1000);

    const display = `${padNumber(hours)}:${padNumber(minutes)}:${padNumber(seconds)}`;
    const timerElement = document.getElementById('workout-timer');
    if (timerElement) {
        timerElement.textContent = display;
    }
}

function padNumber(number) {
    return number.toString().padStart(2, '0');
}

function toggleTimer() {
    if (isPaused) {
        startTimer();
    } else {
        clearInterval(timerInterval);
        isPaused = true;
        
        const pauseTimerButton = document.getElementById('pause-timer');
        if (pauseTimerButton) {
            pauseTimerButton.textContent = 'Resume Timer';
        }
    }
    hideTimerMenu();
}

function confirmReset() {
    if (resetConfirmationActive) {
        // Actually reset the timer
        clearInterval(timerInterval);
        elapsedTime = 0;
        displayTime(0);
        startTimer();
        resetConfirmationActive = false;
        
        const resetTimerButton = document.getElementById('reset-timer');
        if (resetTimerButton) {
            resetTimerButton.textContent = 'Reset Timer';
        }
        
        hideTimerMenu(); // Only hide after confirmed
    } else {
        // Show confirmation
        resetConfirmationActive = true;
        
        const resetTimerButton = document.getElementById('reset-timer');
        if (resetTimerButton) {
            resetTimerButton.textContent = 'Click again to confirm reset';
        }
        
        // Reset the confirmation state after 3 seconds
        if (resetTimeout) {
            clearTimeout(resetTimeout);
        }
        resetTimeout = setTimeout(() => {
            resetConfirmationActive = false;
            
            const resetTimerButton = document.getElementById('reset-timer');
            if (resetTimerButton) {
                resetTimerButton.textContent = 'Reset Timer';
            }
        }, 3000);
    }
}

function toggleTimerMenu() {
    const menu = document.getElementById('timer-menu');
    if (menu) {
        menu.classList.toggle('show');
        
        // Reset the confirmation state when opening/closing menu
        if (!menu.classList.contains('show')) {
            resetConfirmationActive = false;
            
            const resetTimerButton = document.getElementById('reset-timer');
            if (resetTimerButton) {
                resetTimerButton.textContent = 'Reset Timer';
            }
            
            if (resetTimeout) {
                clearTimeout(resetTimeout);
            }
        }
    }
}

function hideTimerMenu() {
    const menu = document.getElementById('timer-menu');
    if (menu) {
        menu.classList.remove('show');
    }
}

// Hide menu when clicking outside
document.addEventListener('click', function(event) {
    const timerContainer = document.querySelector('.timer-container');
    if (timerContainer && !timerContainer.contains(event.target)) {
        hideTimerMenu();
    }
});

// Get actual duration when completing workout
function getWorkoutDuration() {
    return Math.floor(elapsedTime / 1000); // Convert to seconds, not minutes
}