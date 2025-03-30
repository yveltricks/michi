// File: app/static/js/workout.js

// Store workout data
let workoutData = {
    exercises: []
  };
  
  const SET_TYPES = {
    normal: { label: '', color: '#000000', displayName: 'Normal' },
    warmup: { label: ' (W)', color: '#FFA500', displayName: 'Warm up' },
    failure: { label: ' (F)', color: '#FF0000', displayName: 'Failure' },
    drop: { label: ' (D)', color: '#800080', displayName: 'Drop' },
    right: { label: ' (R)', color: '#008000', displayName: 'Right' },
    left: { label: ' (L)', color: '#0000FF', displayName: 'Left' },
    negative: { label: ' (N)', color: '#FF4500', displayName: 'Negative' },
    partial: { label: ' (P)', color: '#4B0082', displayName: 'Partial' }
  };
  
  let currentSetTypeSelection = { exerciseIndex: null, setIndex: null };
  
  const INPUT_CONFIGS = {
    weight_reps: [
        { type: 'number', step: '0.1', min: '0', label: 'Weight (kg)', field: 'weight', class: 'weight-input' },
        { type: 'number', min: '1', step: '1', label: 'Reps', field: 'reps', class: 'reps-input' }
    ],
    bodyweight_reps: [
        { type: 'number', min: '1', step: '1', label: 'Reps', field: 'reps', class: 'reps-input' }
    ],
    weighted_bodyweight: [
        { type: 'number', step: '0.1', min: '0', label: 'Added Weight (kg)', field: 'additional_weight', class: 'weight-input' },
        { type: 'number', min: '1', step: '1', label: 'Reps', field: 'reps', class: 'reps-input' }
    ],
    assisted_bodyweight: [
        { type: 'number', step: '0.1', min: '0', label: 'Assist Weight (kg)', field: 'assistance_weight', class: 'weight-input' },
        { type: 'number', min: '1', step: '1', label: 'Reps', field: 'reps', class: 'reps-input' }
    ],
    duration: [
        { 
            type: 'time',
            field: 'time',
            class: 'time-input-container'
        }
    ],
    duration_weight: [
        { type: 'number', step: '0.1', min: '0', label: 'Weight (kg)', field: 'weight', class: 'weight-input' },
        { type: 'time', field: 'time', class: 'time-input-container' }
    ],
    distance_duration: [
        { type: 'number', step: '0.01', min: '0', label: 'Distance (km)', field: 'distance', class: 'distance-input' },
        { type: 'time', field: 'time', class: 'time-input-container' }
    ],
    weight_distance: [
        { type: 'number', step: '0.1', min: '0', label: 'Weight (kg)', field: 'weight', class: 'weight-input' },
        { type: 'number', step: '0.01', min: '0', label: 'Distance (km)', field: 'distance', class: 'distance-input' }
    ]
};
  
  function addExerciseAndStayOpen(exerciseId, exerciseName) {
    // Fetch exercise details including input type and previous values
    console.log(`Fetching details for exercise ID: ${exerciseId}`);
    
    fetch(`/workout/api/exercise-details/${exerciseId}`)
      .then(response => response.json())
      .then(data => {
            console.log('Exercise details:', data);
            
            // Create a new exercise structure
            const newExercise = {
          id: exerciseId,
          name: exerciseName,
          input_type: data.input_type,
                sets: [],
                range_enabled: data.range_enabled,
                min_reps: data.min_reps,
                max_reps: data.max_reps,
                min_duration: data.min_duration,
                max_duration: data.max_duration,
                min_distance: data.min_distance,
                max_distance: data.max_distance,
                previousSets: data.previousSets || [],
                // Add the rest timer duration from the server data
                rest_duration: data.rest_duration
            };
            
            // Add exercise to workout data
            workoutData.exercises.push(newExercise);
            const exerciseIndex = workoutData.exercises.length - 1;
            
            // Add sets based on previous workout
            if (data.previousSets && data.previousSets.length > 0) {
                // Add each set from the previous workout
                console.log(`Adding ${data.previousSets.length} sets from previous workout`);
                
                // Add a set for each previous set
                data.previousSets.forEach((previousSet, index) => {
                    addSetWithPrevious(exerciseIndex, previousSet, data);
                });
            } else {
                // Add just one empty set
                console.log('No previous sets, adding a default empty set');
                const defaultSet = {
                    ...generateDefaultSetValues(data.input_type),
            completed: false,
            set_type: 'normal',
                    hasPrevious: false
        };
                workoutData.exercises[exerciseIndex].sets.push(defaultSet);
            }
            
            // Update the UI
        renderExercises();
            
            // Sync workout timer in case this is a duration exercise
            syncWorkoutTimer();
        })
        .catch(error => {
            console.error('Error fetching exercise details:', error);
            alert('Error adding exercise. Please try again.');
        });
  }
  
  function addSetWithPrevious(exerciseIndex, previousSet, exerciseData) {
    const exercise = workoutData.exercises[exerciseIndex];
    
    // Create new set with default values
    const newSet = {
        ...generateDefaultSetValues(exercise.input_type),
        completed: false,
        set_type: 'normal',
        hasPrevious: previousSet ? true : false,
        prevValues: previousSet || null,
        isRecommended: {}
    };
    
    // Apply previous set type immediately if available
    if (previousSet && previousSet.set_type) {
        newSet.set_type = previousSet.set_type;
    }
    
    // Apply recommended values if range is enabled and exercise data is available
    if (exercise.range_enabled && exerciseData && previousSet) {
        console.log(`Calculating recommended values for set ${exercise.sets.length + 1} of ${exercise.name}`);
        
        // If we have exercise data with previousSets, use it to calculate recommendations
        const previousSets = exerciseData.previousSets || [];
        const recommendedValues = calculateRecommendedValues(exerciseData, previousSets);
        
        console.log('Recommended values:', recommendedValues);
        
        // Apply recommended values to the set
        if (recommendedValues) {
            // Save which fields are recommendations
            if (recommendedValues.isRecommended) {
                newSet.isRecommended = recommendedValues.isRecommended;
                delete recommendedValues.isRecommended;
            }
            
            // Apply each recommended value if it exists
            Object.keys(recommendedValues).forEach(field => {
                if (recommendedValues[field] !== null && recommendedValues[field] !== undefined) {
                    newSet[field] = recommendedValues[field];
                }
            });
        }
    }
    
    exercise.sets.push(newSet);
  }
  
  function generateDefaultSetValues(inputType) {
    const defaults = {
      'weight_reps': { weight: 0, reps: 0 },
      'bodyweight_reps': { reps: 0 },
      'weighted_bodyweight': { additional_weight: 0, reps: 0 },
      'assisted_bodyweight': { assistance_weight: 0, reps: 0 },
      'duration': { time: 0 },
      'duration_weight': { weight: 0, time: 0 },
      'distance_duration': { distance: 0, time: 0 },
      'weight_distance': { weight: 0, distance: 0 }
    };
    return defaults[inputType] || {};
  }
  
  function formatTime(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  function renderSetInputs(exercise, exerciseIndex, setIndex, set) {
    const configs = INPUT_CONFIGS[exercise.input_type] || [];
    return configs.map(config => {
        if (config.type === 'time') {
            const seconds = set[config.field] || 0;
            // Only show formatted time if there's a non-zero value, otherwise leave empty
            const displayValue = seconds > 0 ? formatTime(seconds) : '';
            
            return `
                <div class="${config.class}">
                    <label class="input-label">Duration</label>
                    <input type="text"
                           value="${displayValue}"
                           placeholder="hh:mm:ss"
                           class="time-input"
                           pattern="[0-9:]*"
                           oninput="handleTimeInput(this, ${exerciseIndex}, ${setIndex}, '${config.field}')"
                           onkeydown="handleTimeKeyDown(this, event)">
                </div>
            `;
        }
        // Show a "recommended" indicator for weight inputs if value came from recommendation
        const isRecommended = set.isRecommended && set.isRecommended[config.field];
        const recommendedClass = isRecommended ? 'recommended-value' : '';
        
        return `
            <div class="input-field-container">
                <label class="input-label">${config.label}${isRecommended ? ' (Recommended)' : ''}</label>
                <input type="${config.type}" 
                       step="${config.step}" 
                       min="${config.min}" 
                       value="${set[config.field] || 0}"
                       onchange="updateSet(${exerciseIndex}, ${setIndex}, '${config.field}', this.value)"
                       class="${config.class} ${recommendedClass}">
            </div>
        `;
    }).join('');
  }
  
  function updateSet(exerciseIndex, setIndex, field, value) {
    const set = workoutData.exercises[exerciseIndex].sets[setIndex];
    const numValue = parseFloat(value);
    
    if (!isNaN(numValue) && numValue >= 0) {
      set[field] = numValue;
    }
    
    renderExercises();
  }
  
  function showSetTypeModal(exerciseIndex, setIndex) {
    console.log('Showing modal for:', exerciseIndex, setIndex); // Debug log
    const modal = document.getElementById('set-type-modal');
    const setTypeList = document.getElementById('set-type-list');
    currentSetTypeSelection = { exerciseIndex, setIndex };
  
    // Clear and populate the set type list
    setTypeList.innerHTML = Object.entries(SET_TYPES).map(([type, info]) => `
        <div class="set-type-option" data-type="${type}">
            <div class="set-type-info">
                <h4 style="color: ${info.color}">${info.displayName}${info.label}</h4>
            </div>
            <button class="select-btn">Select</button>
        </div>
    `).join('');
  
    // Add click handlers for the options
    setTypeList.querySelectorAll('.set-type-option').forEach(option => {
        const selectBtn = option.querySelector('.select-btn');
        selectBtn.addEventListener('click', () => {
            const newType = option.dataset.type;
            console.log('Selected type:', newType); // Debug log
            workoutData.exercises[exerciseIndex].sets[setIndex].set_type = newType;
            modal.style.display = 'none';
            renderExercises();
        });
    });
  
    modal.style.display = 'block';
  }
  
  function toggleSetCompletion(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets[setIndex].completed = 
        !workoutData.exercises[exerciseIndex].sets[setIndex].completed;
    renderExercises();
  }
  
  function addSet(exerciseIndex) {
    const exercise = workoutData.exercises[exerciseIndex];
    const setIndex = exercise.sets.length;
    
    // Check if there's a previous set with this index from the last workout
    let previousSet = null;
    if (exercise.previousSets && setIndex < exercise.previousSets.length) {
        previousSet = exercise.previousSets[setIndex];
    }
    
    // Get exercise data for recommendation calculations
    const exerciseData = {
      input_type: exercise.input_type,
      range_enabled: exercise.range_enabled,
      recommend_enabled: true, // Use the user's setting if available
      min_reps: exercise.min_reps,
      max_reps: exercise.max_reps,
      min_duration: exercise.min_duration,
      max_duration: exercise.max_duration,
      min_distance: exercise.min_distance,
      max_distance: exercise.max_distance,
      previousSets: exercise.previousSets || []
    };
    
    addSetWithPrevious(exerciseIndex, previousSet, exerciseData);
    renderExercises();
  }
  
  function removeSet(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets.splice(setIndex, 1);
    if (workoutData.exercises[exerciseIndex].sets.length === 0) {
        workoutData.exercises.splice(exerciseIndex, 1);
    }
    renderExercises();
  }
  
  function formatSets(sets) {
    const completedSets = sets.filter(set => set.completed).length;
    return `${completedSets} completed set${completedSets !== 1 ? 's' : ''}`;
  }
  
  function showPreviousValues(exerciseIndex, setIndex) {
    const set = workoutData.exercises[exerciseIndex].sets[setIndex];
    if (!set.hasPrevious) {
        alert('No previous values available for this exercise.');
        return;
    }

    const prevValues = set.prevValues;
    
    // Reset any recommended flag
    set.isRecommended = {};
    
    // Update all fields with previous values
    if (prevValues.weight !== undefined && prevValues.weight !== null) {
        updateSet(exerciseIndex, setIndex, 'weight', prevValues.weight);
    }
    
    if (prevValues.reps !== undefined && prevValues.reps !== null) {
        updateSet(exerciseIndex, setIndex, 'reps', prevValues.reps);
    }
    
    if (prevValues.time !== undefined && prevValues.time !== null) {
        updateSet(exerciseIndex, setIndex, 'time', prevValues.time);
    }
    
    if (prevValues.distance !== undefined && prevValues.distance !== null) {
        updateSet(exerciseIndex, setIndex, 'distance', prevValues.distance);
    }
    
    if (prevValues.additional_weight !== undefined && prevValues.additional_weight !== null) {
        updateSet(exerciseIndex, setIndex, 'additional_weight', prevValues.additional_weight);
    }
    
    if (prevValues.assistance_weight !== undefined && prevValues.assistance_weight !== null) {
        updateSet(exerciseIndex, setIndex, 'assistance_weight', prevValues.assistance_weight);
    }
    
    // Also set the set type if available
    if (prevValues.set_type) {
        workoutData.exercises[exerciseIndex].sets[setIndex].set_type = prevValues.set_type;
    }
    
    renderExercises();
  }
  
  function showRangeSettings(exerciseIndex) {
    currentExerciseIndex = exerciseIndex;
    const exercise = workoutData.exercises[exerciseIndex];
    const modal = document.getElementById('range-settings-modal');
    const rangeInputs = document.getElementById('range-inputs');
    const saveButton = document.getElementById('save-range-settings');
    const closeButton = modal.querySelector('.close');
    
    // Set range enabled toggle value based on exercise settings
    const rangeEnabledCheckbox = document.getElementById('range-enabled-checkbox');
    rangeEnabledCheckbox.checked = exercise.range_enabled !== false;

    // Clear previous inputs
    rangeInputs.innerHTML = '';

    // Add range inputs based on exercise type
    if (exercise.input_type.includes('reps')) {
        rangeInputs.innerHTML += `
            <div class="range-input-group">
                <label>Min Reps:</label>
                <input type="number" id="min-reps" value="${exercise.min_reps || ''}" min="1">
            </div>
            <div class="range-input-group">
                <label>Max Reps:</label>
                <input type="number" id="max-reps" value="${exercise.max_reps || ''}" min="1">
            </div>
        `;
    }

    if (exercise.input_type.includes('duration')) {
        // Convert seconds to formatted time for display
        const minDurationFormatted = exercise.min_duration ? formatTime(exercise.min_duration) : '';
        const maxDurationFormatted = exercise.max_duration ? formatTime(exercise.max_duration) : '';
        
        rangeInputs.innerHTML += `
            <div class="range-input-group">
                <label>Min Duration:</label>
                <input type="text" id="min-duration" value="${minDurationFormatted}" 
                       placeholder="hh:mm:ss" class="time-input" pattern="[0-9:]*"
                       oninput="handleRangeTimeInput(this, 'min')"
                       onkeydown="handleTimeKeyDown(this, event)">
                <input type="hidden" id="min-duration-seconds" value="${exercise.min_duration || ''}">
            </div>
            <div class="range-input-group">
                <label>Max Duration:</label>
                <input type="text" id="max-duration" value="${maxDurationFormatted}" 
                       placeholder="hh:mm:ss" class="time-input" pattern="[0-9:]*"
                       oninput="handleRangeTimeInput(this, 'max')"
                       onkeydown="handleTimeKeyDown(this, event)">
                <input type="hidden" id="max-duration-seconds" value="${exercise.max_duration || ''}">
            </div>
        `;
    }

    if (exercise.input_type.includes('distance')) {
        rangeInputs.innerHTML += `
            <div class="range-input-group">
                <label>Min Distance (km):</label>
                <input type="number" id="min-distance" value="${exercise.min_distance || ''}" min="0" step="0.01">
            </div>
            <div class="range-input-group">
                <label>Max Distance (km):</label>
                <input type="number" id="max-distance" value="${exercise.max_distance || ''}" min="0" step="0.01">
            </div>
        `;
    }

    // Add event listeners for save and close buttons
    saveButton.onclick = saveRangeSettings;
    closeButton.onclick = function() {
        modal.style.display = 'none';
    };

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // Show modal
    modal.style.display = 'block';
  }
  
  // Add a function to handle time input for range settings
  function handleRangeTimeInput(input, type) {
    // Check if this is a digit being entered
    if (/^\d$/.test(event.data)) {
        // Store raw digits in a data attribute
        if (!input.dataset.rawDigits) {
            input.dataset.rawDigits = '';
        }
        
        // Add the new digit
        input.dataset.rawDigits += event.data;
        
        // Limit to 6 digits
        if (input.dataset.rawDigits.length > 6) {
            input.dataset.rawDigits = input.dataset.rawDigits.slice(-6);
        }
    } 
    // Handle backspace/delete
    else if (event.inputType === 'deleteContentBackward' || event.inputType === 'deleteContentForward') {
        if (input.dataset.rawDigits) {
            input.dataset.rawDigits = input.dataset.rawDigits.slice(0, -1);
        }
    }
    
    // Format the time based on raw digits
    let formattedValue = '';
    let totalSeconds = 0;
    const rawDigits = input.dataset.rawDigits || '';
    
    if (rawDigits.length > 0) {
        // Calculate seconds, minutes, hours from right to left
        const len = rawDigits.length;
        
        // Right-align the digits (for values like seconds, minutes, hours)
        let seconds = 0, minutes = 0, hours = 0;
        
        // Process from right to left (least significant to most significant)
        if (len >= 1) seconds += parseInt(rawDigits.charAt(len-1));  // 1s place
        if (len >= 2) seconds += parseInt(rawDigits.charAt(len-2)) * 10;  // 10s place
        
        if (len >= 3) minutes += parseInt(rawDigits.charAt(len-3));  // 1s place
        if (len >= 4) minutes += parseInt(rawDigits.charAt(len-4)) * 10;  // 10s place
        
        if (len >= 5) hours += parseInt(rawDigits.charAt(len-5));  // 1s place
        if (len >= 6) hours += parseInt(rawDigits.charAt(len-6)) * 10;  // 10s place
        
        formattedValue = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        totalSeconds = hours * 3600 + minutes * 60 + seconds;
    }
    
    // Update the input value
    input.value = formattedValue;
    
    // Update the hidden field with the seconds value
    const hiddenField = document.getElementById(`${type}-duration-seconds`);
    if (hiddenField) {
        hiddenField.value = totalSeconds;
    }
  }
  
  function saveRangeSettings() {
    if (currentExerciseIndex === null) return;

    const exercise = workoutData.exercises[currentExerciseIndex];
    const modal = document.getElementById('range-settings-modal');
    const rangeEnabledCheckbox = document.getElementById('range-enabled-checkbox');
    let minReps, maxReps, minDuration, maxDuration, minDistance, maxDistance;
    
    // Get the range enabled status
    const rangeEnabled = rangeEnabledCheckbox.checked;
    
    // Get and validate inputs
    if (exercise.input_type.includes('reps')) {
        minReps = document.getElementById('min-reps').value;
        maxReps = document.getElementById('max-reps').value;
        
        if (minReps && maxReps) {
            minReps = parseInt(minReps);
            maxReps = parseInt(maxReps);
            
            if (isNaN(minReps) || isNaN(maxReps)) {
                alert('Please enter valid numbers for rep ranges');
                return;
            }
            
            if (minReps > maxReps) {
                alert('Minimum reps cannot be greater than maximum reps');
                return;
            }
        }
    }

    if (exercise.input_type.includes('duration')) {
        // Get from the hidden fields that store seconds
        minDuration = document.getElementById('min-duration-seconds').value;
        maxDuration = document.getElementById('max-duration-seconds').value;
        
        if (minDuration && maxDuration) {
            minDuration = parseInt(minDuration);
            maxDuration = parseInt(maxDuration);
            
            if (isNaN(minDuration) || isNaN(maxDuration)) {
                alert('Please enter valid numbers for duration ranges');
                return;
            }
            
            if (minDuration > maxDuration) {
                alert('Minimum duration cannot be greater than maximum duration');
                return;
            }
        }
    }

    if (exercise.input_type.includes('distance')) {
        minDistance = document.getElementById('min-distance').value;
        maxDistance = document.getElementById('max-distance').value;
        
        if (minDistance && maxDistance) {
            minDistance = parseFloat(minDistance);
            maxDistance = parseFloat(maxDistance);
            
            if (isNaN(minDistance) || isNaN(maxDistance)) {
                alert('Please enter valid numbers for distance ranges');
                return;
            }
            
            if (minDistance > maxDistance) {
                alert('Minimum distance cannot be greater than maximum distance');
                return;
            }
        }
    }

    // Create payload
    const payload = {
        range_enabled: rangeEnabled,
        min_reps: minReps || null,
        max_reps: maxReps || null,
        min_duration: minDuration || null,
        max_duration: maxDuration || null,
        min_distance: minDistance || null,
        max_distance: maxDistance || null
    };
    
    console.log("Sending range settings:", payload); // Debug log

    // Save to server
    fetch(`/workout/api/exercise-ranges/${exercise.id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            // Check if there's an HTML response (error page)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                throw new Error('Server returned an HTML error page. Please check server logs.');
            }
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update exercise data with returned values
            exercise.min_reps = data.min_reps;
            exercise.max_reps = data.max_reps;
            exercise.min_duration = data.min_duration;
            exercise.max_duration = data.max_duration;
            exercise.min_distance = data.min_distance;
            exercise.max_distance = data.max_distance;
            exercise.range_enabled = data.range_enabled;
            
            // Close modal and refresh UI
            modal.style.display = 'none';
            renderExercises();
        } else {
            alert('Error saving range settings: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving range settings: ' + error.message);
    });
  }
  
  function formatPreviousValues(set) {
    if (!set.hasPrevious || !set.prevValues) return 'No Previous';
    
    const values = set.prevValues;
    const parts = [];
    
    if (values.weight !== undefined && values.weight !== null) {
        parts.push(`${values.weight}kg`);
    }
    
    if (values.additional_weight !== undefined && values.additional_weight !== null) {
        parts.push(`+${values.additional_weight}kg`);
    }
    
    if (values.assistance_weight !== undefined && values.assistance_weight !== null) {
        parts.push(`-${values.assistance_weight}kg`);
    }
    
    if (values.reps !== undefined && values.reps !== null) {
        parts.push(`${values.reps} reps`);
    }
    
    if (values.time !== undefined && values.time !== null) {
        parts.push(formatTime(values.time));
    }
    
    if (values.distance !== undefined && values.distance !== null) {
        parts.push(`${values.distance}km`);
    }
    
    return parts.length > 0 ? parts.join(' × ') : 'No Previous';
  }
  
  function formatRangeSettings(exercise) {
    if (!exercise.range_enabled) return 'Range: Off';
    
    const parts = [];
    
    // Check for reps range
    if (exercise.min_reps !== null && exercise.max_reps !== null && 
        exercise.min_reps !== undefined && exercise.max_reps !== undefined && 
        !isNaN(exercise.min_reps) && !isNaN(exercise.max_reps)) {
        parts.push(`${exercise.min_reps}-${exercise.max_reps} reps`);
    }
    
    // Check for duration range
    if (exercise.min_duration !== null && exercise.max_duration !== null && 
        exercise.min_duration !== undefined && exercise.max_duration !== undefined && 
        !isNaN(exercise.min_duration) && !isNaN(exercise.max_duration)) {
        parts.push(`${exercise.min_duration}-${exercise.max_duration}s`);
    }
    
    // Check for distance range
    if (exercise.min_distance !== null && exercise.max_distance !== null && 
        exercise.min_distance !== undefined && exercise.max_distance !== undefined && 
        !isNaN(exercise.min_distance) && !isNaN(exercise.max_distance)) {
        parts.push(`${exercise.min_distance}-${exercise.max_distance}km`);
    }
    
    return parts.length > 0 ? `Range: ${parts.join(', ')}` : 'Range: Set';
  }
  
  function renderExercises() {
    const container = document.getElementById('exercises-container');
    container.innerHTML = '';
  
    // First reset performance metrics to recalculate
    let shouldRecalculatePerformance = false;
    
    // Check if we have any completed sets that need performance recalculation
    workoutData.exercises.forEach(exercise => {
      exercise.sets.forEach(set => {
        if (set.completed && set.hasPrevious && set.prevValues) {
          shouldRecalculatePerformance = true;
        }
      });
    });
    
    // If we need to recalculate, reset first
    if (shouldRecalculatePerformance) {
      resetPerformanceMetrics();
      
      // Then analyze all completed sets
      workoutData.exercises.forEach(exercise => {
        exercise.sets.forEach(set => {
          if (set.completed && set.hasPrevious && set.prevValues) {
            updatePerformanceMetrics(exercise, set, set.prevValues, true);
          }
        });
      });
    }
  
    workoutData.exercises.forEach((exercise, exerciseIndex) => {
        const exerciseDiv = document.createElement('div');
        exerciseDiv.className = 'exercise-entry';
  
        let setsHtml = exercise.sets.map((set, setIndex) => {
            const setType = SET_TYPES[set.set_type || 'normal'];
            
            // Don't update stats counters here - they're updated in handleSetCompletion
            
            return `
                <div class="set-entry ${set.completed ? 'checked' : ''}">
                    <span class="set-label" 
                          onclick="showSetTypeModal(${exerciseIndex}, ${setIndex})"
                          style="color: ${setType.color}; cursor: pointer;">
                        Set ${setIndex + 1}${setType.label}
                    </span>
                    ${renderSetInputs(exercise, exerciseIndex, setIndex, set)}
                    <button onclick="showPreviousValues(${exerciseIndex}, ${setIndex})" 
                            class="previous-values-btn ${set.hasPrevious ? '' : 'no-data'}">
                        ${formatPreviousValues(set)}
                    </button>
                    <label class="set-complete-checkbox">
                        <input type="checkbox"
                            ${set.completed ? 'checked' : ''}
                            onchange="handleSetCompletion(${exerciseIndex}, ${setIndex})">
                        <span class="checkmark"></span>
                    </label>
                    <button onclick="removeSet(${exerciseIndex}, ${setIndex})" class="remove-set-btn">×</button>
                </div>
            `;
        }).join('');
  
        const restTimerText = exercise.rest_duration ? formatRestDuration(exercise.rest_duration) : 'No Rest Timer';
  
        exerciseDiv.innerHTML = `
            <div class="exercise-header">
                <h3 class="exercise-title">${exercise.name} (${formatSets(exercise.sets)})</h3>
                <div class="exercise-actions">
                    <button onclick="showRestSettingsModal(${exerciseIndex})" class="rest-timer-btn">
                        Rest: ${restTimerText}
                    </button>
                    <button onclick="showRangeSettings(${exerciseIndex})" class="range-settings-btn">
                        ${formatRangeSettings(exercise)}
                    </button>
                </div>
            </div>
            <div class="sets-container">
                ${setsHtml}
            </div>
            <button onclick="addSet(${exerciseIndex})" class="add-set-btn">
                + Add Set
            </button>
        `;
  
        container.appendChild(exerciseDiv);
    });
    
    // Update EXP display
    updateExpDisplay();
  }
  
  // Handle muscle group filtering
  document.addEventListener('DOMContentLoaded', function() {
    const muscleFilter = document.getElementById('muscle-filter');
    if (muscleFilter) {
        muscleFilter.addEventListener('change', function() {
            const selectedMuscle = this.value.toLowerCase();
            const exercises = document.querySelectorAll('.exercise-option');
            
            exercises.forEach(exercise => {
                const muscles = exercise.dataset.muscles.toLowerCase();
                if (selectedMuscle === 'all' || muscles.includes(selectedMuscle)) {
                    exercise.style.display = '';
                } else {
                    exercise.style.display = 'none';
                }
            });
        });
    }
  });
  
  // Handle form submission
  function completeWorkout() {
    if (workoutData.exercises.length === 0) {
        alert("Please add at least one exercise to your workout.");
        return;
    }
  
    // Filter out exercises with no completed sets
    const completedExercises = workoutData.exercises.map(exercise => ({
        ...exercise,
        sets: exercise.sets.filter(set => set.completed)
    })).filter(exercise => exercise.sets.length > 0);
  
    if (completedExercises.length === 0) {
        alert("Please complete at least one set before finishing the workout.");
        return;
    }
  
    const data = {
        exercises: completedExercises,
        title: document.getElementById('workout-title').value.trim() || 'Workout',
        description: document.getElementById('workout-description').value,
        rating: document.getElementById('workout-rating').value,
        duration: calculateWorkoutDuration(),
        exp_gained: sessionExpGained, // Include the session EXP
        volume: totalVolume // Include total volume
    };
  
    // Log the data being sent
    console.log('Sending workout data:', data);
  
    // Show loading indicator
    document.querySelector('.finish-workout-btn').disabled = true;
    document.querySelector('.finish-workout-btn').textContent = 'Saving...';
  
    // Send data to server
    fetch('/workout/log-workout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        console.log('Response status:', response.status);
        // Check if response is OK before trying to parse as JSON
        if (!response.ok) {
            return response.text().then(text => {
                console.error('Server error response:', text);
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Server response:', data);
        if (data.success) {
            window.location.href = '/workout/session/' + data.session_id;
        } else {
            alert('Error saving workout: ' + (data.error || 'Unknown error'));
            // Re-enable button
            document.querySelector('.finish-workout-btn').disabled = false;
            document.querySelector('.finish-workout-btn').textContent = 'Complete Workout';
        }
    })
    .catch((error) => {
        console.error('Error details:', error);
        alert('Error saving workout: ' + error.message);
        // Re-enable button
        document.querySelector('.finish-workout-btn').disabled = false;
        document.querySelector('.finish-workout-btn').textContent = 'Complete Workout';
    });
  }
  
  // Calculate workout duration
  function calculateWorkoutDuration() {
    // Get timer duration in seconds
    const timerDurationSeconds = getWorkoutDuration();
    
    // Find the longest exercise duration in seconds
    let maxExerciseDurationSeconds = 0;
    workoutData.exercises.forEach(exercise => {
        exercise.sets.forEach(set => {
            if (set.time && set.time > maxExerciseDurationSeconds) {
                maxExerciseDurationSeconds = set.time;
            }
        });
    });
    
    console.log('Timer duration (s):', timerDurationSeconds, 'Longest exercise (s):', maxExerciseDurationSeconds);
    
    // Get the maximum between timer and exercise duration (in seconds)
    const maxDurationSeconds = Math.max(timerDurationSeconds, maxExerciseDurationSeconds);
    
    // Convert seconds to minutes before returning (to maintain compatibility with existing code)
    const durationMinutes = Math.ceil(maxDurationSeconds / 60);
    console.log('Final duration (min):', durationMinutes);
    
    return durationMinutes; // Return minutes for database storage
  }

  // Add this function above the handleTimeInput function
  function handleTimeKeyDown(input, event) {
    // Only allow digits, backspace, delete, tab, arrows
    const allowedKeys = ['Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'];
    if (!/^\d$/.test(event.key) && !allowedKeys.includes(event.key)) {
        event.preventDefault();
    }
  }

  function handleTimeInput(input, exerciseIndex, setIndex, field) {
    // Check if this is a digit being entered
    if (/^\d$/.test(event.data)) {
        // Store raw digits in a data attribute
        if (!input.dataset.rawDigits) {
            input.dataset.rawDigits = '';
        }
        
        // Add the new digit
        input.dataset.rawDigits += event.data;
        
        // Limit to 6 digits
        if (input.dataset.rawDigits.length > 6) {
            input.dataset.rawDigits = input.dataset.rawDigits.slice(-6);
        }
    } 
    // Handle backspace/delete
    else if (event.inputType === 'deleteContentBackward' || event.inputType === 'deleteContentForward') {
        if (input.dataset.rawDigits) {
            input.dataset.rawDigits = input.dataset.rawDigits.slice(0, -1);
        }
    }
    
    // Format the time based on raw digits
    let formattedValue = '';
    let totalSeconds = 0;
    const rawDigits = input.dataset.rawDigits || '';
    
    if (rawDigits.length > 0) {
        // Calculate seconds, minutes, hours from right to left
        const len = rawDigits.length;
        
        // Right-align the digits (for values like seconds, minutes, hours)
        let seconds = 0, minutes = 0, hours = 0;
        
        // Process from right to left (least significant to most significant)
        if (len >= 1) seconds += parseInt(rawDigits.charAt(len-1));  // 1s place
        if (len >= 2) seconds += parseInt(rawDigits.charAt(len-2)) * 10;  // 10s place
        
        if (len >= 3) minutes += parseInt(rawDigits.charAt(len-3));  // 1s place
        if (len >= 4) minutes += parseInt(rawDigits.charAt(len-4)) * 10;  // 10s place
        
        if (len >= 5) hours += parseInt(rawDigits.charAt(len-5));  // 1s place
        if (len >= 6) hours += parseInt(rawDigits.charAt(len-6)) * 10;  // 10s place
        
        formattedValue = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        totalSeconds = hours * 3600 + minutes * 60 + seconds;
    }
    
    // Update the input value
    input.value = formattedValue;
    
    // Update data model
    workoutData.exercises[exerciseIndex].sets[setIndex][field] = totalSeconds;
    
    // Sync with workout timer if needed
    syncWorkoutTimer();
  }

  // Function to synchronize the workout timer with the longest exercise duration
  function syncWorkoutTimer() {
    // Find the longest duration across all exercises
    let maxDuration = 0;
    
    workoutData.exercises.forEach(exercise => {
        exercise.sets.forEach(set => {
            if (set.time && set.time > maxDuration) {
                maxDuration = set.time;
            }
        });
    });
    
    console.log('Longest exercise duration:', maxDuration);
    
    // Skip if no significant duration found
    if (maxDuration <= 0) return;
    
    // Get the current timer value
    const timerElement = document.getElementById('workout-timer');
    if (!timerElement) return;
    
    // Always use the longest duration from exercises as the minimum workout time
    const currentTimerValue = parseInt(timerElement.dataset.seconds || 0);
    
    // Update the timer if exercise duration is longer than current timer
    if (maxDuration > currentTimerValue) {
        console.log('Updating workout timer to match longest exercise:', formatTime(maxDuration));
        
        // Update the timer value in the global scope
        if (typeof window.seconds !== 'undefined') {
            window.seconds = maxDuration;
        }
        
        // Update the display
        if (typeof updateTimerDisplay === 'function') {
            updateTimerDisplay();
        } else {
            // Fallback if the function isn't available
            timerElement.textContent = formatTime(maxDuration);
            timerElement.dataset.seconds = maxDuration;
        }
    }
  }

  // Function to calculate recommended values based on previous performance
  function calculateRecommendedValues(exerciseData, previousSets) {
    console.log('Starting recommendation calculation with data:', { 
      inputType: exerciseData.input_type,
      rangeEnabled: exerciseData.range_enabled,
      minReps: exerciseData.min_reps,
      maxReps: exerciseData.max_reps,
      previousSetsCount: previousSets?.length || 0
    });
    
    // If ranges are disabled or no previous sets, no recommendations
    if (!exerciseData.range_enabled || !previousSets || previousSets.length === 0) {
      console.log('Cannot make recommendations: ranges disabled or no previous sets');
      return null;
    }
    
    // Check if recommendations are enabled globally (gets passed from the server in exerciseData)
    if (exerciseData.recommend_enabled === false) {
      console.log('Recommendations are disabled in user settings');
      return null;
    }
    
    const inputType = exerciseData.input_type;
    // Get last 3 sets or all
    const recentSets = previousSets.slice(-3);
    console.log('Using most recent sets for calculation:', recentSets);
    
    // Initialize recommendation object
    const recommendation = {};
    // Track which fields are recommendations vs copies from previous values
    const isRecommended = {};
    
    // Check if input type uses weight
    if (inputType.includes('weight')) {
      // Find the last weight value used
      let lastWeight = 0;
      for (const set of recentSets) {
        if (set.weight) {
          lastWeight = set.weight;
          break;
        } else if (set.additional_weight) {
          lastWeight = set.additional_weight;
          break;
        }
      }
      
      console.log(`Found last weight: ${lastWeight}`);
      
      // Check if all sets were within or above range for various metrics
      let allUpperRange = true;
      let allLowerRange = true;
      
      if (inputType === 'weight_reps' || inputType === 'bodyweight_reps' || inputType === 'weighted_bodyweight') {
        // Check rep ranges
        if (exerciseData.min_reps !== null && exerciseData.max_reps !== null) {
          console.log(`Checking rep ranges: min=${exerciseData.min_reps}, max=${exerciseData.max_reps}`);
          
          for (const set of recentSets) {
            console.log(`Set reps: ${set.reps}, comparing to min=${exerciseData.min_reps}, max=${exerciseData.max_reps}`);
            
            if (set.reps < exerciseData.max_reps) {
              allUpperRange = false;
              console.log(`Set with ${set.reps} reps is below max ${exerciseData.max_reps}, allUpperRange=${allUpperRange}`);
            }
            if (set.reps > exerciseData.min_reps) {
              allLowerRange = false;
              console.log(`Set with ${set.reps} reps is above min ${exerciseData.min_reps}, allLowerRange=${allLowerRange}`);
            }
          }
          
          // Make weight recommendations based on performance
          if (allUpperRange && lastWeight > 0) {
            // If all sets hit upper range, recommend higher weight
            if (inputType === 'weight_reps') {
              recommendation.weight = Math.round((lastWeight + 2.5) * 10) / 10; // Round to nearest 0.1
              isRecommended.weight = true;
              console.log(`All sets at upper range, recommending higher weight: ${recommendation.weight}`);
            } else if (inputType === 'weighted_bodyweight') {
              recommendation.additional_weight = Math.round((lastWeight + 2.5) * 10) / 10;
              isRecommended.additional_weight = true;
              console.log(`All sets at upper range, recommending higher additional weight: ${recommendation.additional_weight}`);
            }
          } else if (allLowerRange && lastWeight > 0) {
            // If all sets below lower range, recommend lower weight
            if (inputType === 'weight_reps') {
              recommendation.weight = Math.max(0, Math.round((lastWeight - 2.5) * 10) / 10);
              isRecommended.weight = true;
              console.log(`All sets at lower range, recommending lower weight: ${recommendation.weight}`);
            } else if (inputType === 'weighted_bodyweight') {
              recommendation.additional_weight = Math.max(0, Math.round((lastWeight - 2.5) * 10) / 10);
              isRecommended.additional_weight = true;
              console.log(`All sets at lower range, recommending lower additional weight: ${recommendation.additional_weight}`);
            }
          } else if (lastWeight > 0) {
            // If mixed performance, keep same weight
            if (inputType === 'weight_reps') {
              recommendation.weight = lastWeight;
              console.log(`Mixed performance, keeping same weight: ${recommendation.weight}`);
            } else if (inputType === 'weighted_bodyweight') {
              recommendation.additional_weight = lastWeight;
              console.log(`Mixed performance, keeping same additional weight: ${recommendation.additional_weight}`);
            }
          }
        }
      } else if (inputType === 'duration_weight') {
        // Check duration ranges
        if (exerciseData.min_duration !== null && exerciseData.max_duration !== null) {
          for (const set of recentSets) {
            if (set.time < exerciseData.max_duration) {
              allUpperRange = false;
            }
            if (set.time > exerciseData.min_duration) {
              allLowerRange = false;
            }
          }
          
          // Make weight recommendations based on duration performance
          if (allUpperRange && lastWeight > 0) {
            recommendation.weight = Math.round((lastWeight + 2.5) * 10) / 10;
            isRecommended.weight = true;
            console.log(`All duration at upper range, recommending higher weight: ${recommendation.weight}`);
          } else if (allLowerRange && lastWeight > 0) {
            recommendation.weight = Math.max(0, Math.round((lastWeight - 2.5) * 10) / 10);
            isRecommended.weight = true;
            console.log(`All duration at lower range, recommending lower weight: ${recommendation.weight}`);
          } else if (lastWeight > 0) {
            recommendation.weight = lastWeight;
            console.log(`Mixed duration performance, keeping same weight: ${recommendation.weight}`);
          }
        }
      } else if (inputType === 'weight_distance') {
        // Check distance ranges
        if (exerciseData.min_distance !== null && exerciseData.max_distance !== null) {
          for (const set of recentSets) {
            if (set.distance < exerciseData.max_distance) {
              allUpperRange = false;
            }
            if (set.distance > exerciseData.min_distance) {
              allLowerRange = false;
            }
          }
          
          // Make weight recommendations based on distance performance
          if (allUpperRange && lastWeight > 0) {
            recommendation.weight = Math.round((lastWeight + 2.5) * 10) / 10;
            isRecommended.weight = true;
            console.log(`All distance at upper range, recommending higher weight: ${recommendation.weight}`);
          } else if (allLowerRange && lastWeight > 0) {
            recommendation.weight = Math.max(0, Math.round((lastWeight - 2.5) * 10) / 10);
            isRecommended.weight = true;
            console.log(`All distance at lower range, recommending lower weight: ${recommendation.weight}`);
          } else if (lastWeight > 0) {
            recommendation.weight = lastWeight;
            console.log(`Mixed distance performance, keeping same weight: ${recommendation.weight}`);
          }
        }
      }
    }
    
    // Handle pure duration exercises (like planks)
    if (inputType === 'duration') {
      // Get the last duration used
      let lastDuration = 0;
      for (const set of recentSets) {
        if (set.time) {
          lastDuration = set.time;
          break;
        }
      }
      
      let allUpperRange = true;
      let allLowerRange = true;
      
      // Check duration ranges
      if (exerciseData.min_duration !== null && exerciseData.max_duration !== null) {
        for (const set of recentSets) {
          if (!set.time) continue;
          // Check if all sets are at or above the max duration
          if (set.time < exerciseData.max_duration) {
            allUpperRange = false;
          }
          // Check if all sets are below the min duration
          if (set.time > exerciseData.min_duration) {
            allLowerRange = false;
          }
        }
        
        console.log('Duration check:', { lastDuration, min: exerciseData.min_duration, max: exerciseData.max_duration, allUpperRange, allLowerRange });
        
        // Make duration recommendations based on performance
        if (allUpperRange && lastDuration > 0) {
          // If all durations at or above max, recommend 10% longer duration
          const increasedDuration = Math.ceil(lastDuration * 1.1);
          recommendation.time = increasedDuration;
          isRecommended.time = true;
          console.log('Recommending increased duration:', increasedDuration);
        } else if (allLowerRange && lastDuration > 0) {
          // If all durations below min, recommend 10% shorter duration
          const decreasedDuration = Math.max(5, Math.floor(lastDuration * 0.9));
          recommendation.time = decreasedDuration;
          isRecommended.time = true;
          console.log('Recommending decreased duration:', decreasedDuration);
        } else if (lastDuration > 0) {
          // If mixed performance, keep the same duration
          recommendation.time = lastDuration;
          console.log('Keeping same duration:', lastDuration);
        }
      }
    }
    
    // For all other values, just use the previous values
    // This ensures we're only changing certain values based on performance in ranges
    for (const set of recentSets) {
      if (!inputType.includes('duration') && set.reps && !recommendation.reps) {
        recommendation.reps = set.reps;
        console.log(`Using previous reps value: ${recommendation.reps}`);
      }
      if (!inputType.includes('weight') && !inputType.includes('duration') && set.time && !recommendation.time) {
        recommendation.time = set.time;
        console.log(`Using previous time value: ${recommendation.time}`);
      }
      if (!inputType.includes('distance') && set.distance && !recommendation.distance) {
        recommendation.distance = set.distance;
        console.log(`Using previous distance value: ${recommendation.distance}`);
      }
      if (set.assistance_weight && !recommendation.assistance_weight) {
        recommendation.assistance_weight = set.assistance_weight;
        console.log(`Using previous assistance weight value: ${recommendation.assistance_weight}`);
      }
    }
    
    // Add isRecommended flags to the recommendation
    recommendation.isRecommended = isRecommended;
    
    console.log('Final recommendation:', recommendation);
    return recommendation;
  }

  // Rest timer variables
  let currentExerciseIndex = null;
  let restTimerInterval = null;
  let restSeconds = 0;
  let restTotalSeconds = 0;
  let isRestPaused = false;
  let activeRestTimer = false;

  function formatRestDuration(seconds) {
    if (!seconds) return 'Off';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function showRestSettingsModal(exerciseIndex) {
    currentExerciseIndex = exerciseIndex;
    const exercise = workoutData.exercises[exerciseIndex];
    const modal = document.getElementById('rest-timer-modal');
    const minutesInput = document.getElementById('rest-minutes');
    const secondsInput = document.getElementById('rest-seconds');
    const enabledCheckbox = document.getElementById('rest-enabled');
    const saveButton = document.getElementById('save-rest-settings');
    const closeButton = modal.querySelector('.close');
    
    // Set initial values based on exercise settings
    if (exercise.rest_duration) {
        const mins = Math.floor(exercise.rest_duration / 60);
        const secs = exercise.rest_duration % 60;
        minutesInput.value = mins;
        secondsInput.value = secs;
        enabledCheckbox.checked = true;
    } else {
        minutesInput.value = 0;
        secondsInput.value = 0;
        enabledCheckbox.checked = false;
    }
    
    // Add event listeners for save and close buttons
    saveButton.onclick = saveRestSettings;
    closeButton.onclick = function() {
        modal.style.display = 'none';
    };
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
    
    // Show modal
    modal.style.display = 'block';
  }

  function saveRestSettings() {
    if (currentExerciseIndex === null) return;
    
    const exercise = workoutData.exercises[currentExerciseIndex];
    const modal = document.getElementById('rest-timer-modal');
    const minutes = parseInt(document.getElementById('rest-minutes').value) || 0;
    const seconds = parseInt(document.getElementById('rest-seconds').value) || 0;
    const enabled = document.getElementById('rest-enabled').checked;
    
    // Calculate total seconds
    let totalSeconds = null;
    if (enabled && (minutes > 0 || seconds > 0)) {
        totalSeconds = (minutes * 60) + seconds;
    }
    
    // Create payload
    const payload = {
        rest_duration: totalSeconds
    };
    
    console.log("Sending rest timer settings:", payload); // Debug log
    
    // Save to server
    fetch(`/workout/api/exercise-rest/${exercise.id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update exercise data
            exercise.rest_duration = data.rest_duration;
            
            // Close modal and refresh UI
            modal.style.display = 'none';
            renderExercises();
        } else {
            alert('Error saving rest timer: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving rest timer: ' + error.message);
    });
  }

  // Add global variables for tracking exp
  let sessionExpGained = 0;
  let expGainTimeout = null;

  // Add globals for workout stats tracking
  let totalVolume = 0;
  let completedSets = 0;
  let totalReps = 0;
  let performanceData = {
    improved: 0,
    declined: 0,
    neutral: 0,
    totalSetsAnalyzed: 0,
    percentChange: 0
  };

  function handleSetCompletion(exerciseIndex, setIndex) {
    const exercise = workoutData.exercises[exerciseIndex];
    const set = exercise.sets[setIndex];
    
    // Toggle completion status
    const wasCompleted = set.completed;
    set.completed = !set.completed;
    
    // If set was marked as completed (not uncompleted)
    if (set.completed && !wasCompleted) {
        // Calculate EXP gain if there are previous values to compare
        if (set.hasPrevious && set.prevValues) {
            const expGained = calculateExpGain(exercise, set, set.prevValues);
            if (expGained > 0) {
                showExpGain(expGained);
            }
            
            // Calculate performance metrics if we have previous values
            updatePerformanceMetrics(exercise, set, set.prevValues, true);
        } else {
            // Base EXP for completing a set with no previous comparison
            showExpGain(1);
        }
        
        // Update volume, sets, and reps stats
        updateWorkoutStats(exercise, set, true);
        
        // Start rest timer if enabled
        if (exercise.rest_duration) {
            startRestTimer(exercise.rest_duration, exercise.name);
        }
    } else if (!set.completed && wasCompleted) {
        // If set was uncompleted, remove EXP
        // We don't know exactly how much EXP this set contributed, so use a base value
        sessionExpGained = Math.max(0, sessionExpGained - 1);
        updateExpDisplay();
        
        // Update volume, sets, and reps stats
        updateWorkoutStats(exercise, set, false);
        
        // Revert performance metrics if we have previous values
        if (set.hasPrevious && set.prevValues) {
            updatePerformanceMetrics(exercise, set, set.prevValues, false);
        }
    }
    
    renderExercises();
  }

  // Add function to update workout stats
  function updateWorkoutStats(exercise, set, isCompleted) {
    // Update completed sets count
    completedSets = isCompleted ? completedSets + 1 : completedSets - 1;
    document.getElementById('sets-done').textContent = completedSets;
    
    // Update reps based on exercise input type
    if (set.reps) {
        totalReps = isCompleted ? totalReps + parseInt(set.reps) : totalReps - parseInt(set.reps);
        document.getElementById('reps-done').textContent = totalReps;
    }
    
    // Calculate and update volume
    const setVolume = calculateSetVolume(exercise, set);
    totalVolume = isCompleted ? totalVolume + setVolume : totalVolume - setVolume;
    document.getElementById('workout-volume').textContent = Math.round(totalVolume);
  }

  // Function to calculate the volume of a set
  function calculateSetVolume(exercise, set) {
    let volume = 0;
    
    if (exercise.input_type === 'weight_reps' && set.weight && set.reps) {
        // Standard weight × reps volume calculation
        volume = parseFloat(set.weight) * parseInt(set.reps);
    } else if (exercise.input_type === 'weighted_bodyweight' && set.additional_weight && set.reps) {
        // For weighted bodyweight exercises (estimated bodyweight + additional weight) × reps
        const estimatedBodyweight = 75; // Default estimate - could be improved to use user's actual weight
        volume = (estimatedBodyweight + parseFloat(set.additional_weight)) * parseInt(set.reps);
    } else if (exercise.input_type === 'bodyweight_reps' && set.reps) {
        // For bodyweight only, estimate bodyweight × reps
        const estimatedBodyweight = 75; // Default estimate
        volume = estimatedBodyweight * parseInt(set.reps);
    } else if (exercise.input_type === 'assisted_bodyweight' && set.assistance_weight && set.reps) {
        // For assisted bodyweight exercises (estimated bodyweight - assistance weight) × reps
        const estimatedBodyweight = 75; // Default estimate
        const assistWeight = parseFloat(set.assistance_weight);
        volume = Math.max(0, estimatedBodyweight - assistWeight) * parseInt(set.reps);
    }
    
    return volume;
  }

  function startRestTimer(seconds, exerciseName) {
    // Clear any existing rest timer
    if (restTimerInterval) {
        clearInterval(restTimerInterval);
    }
    
    // Setup new rest timer
    restSeconds = seconds;
    restTotalSeconds = seconds;
    isRestPaused = false;
    activeRestTimer = true;
    
    // Show the rest timer container
    const restTimerContainer = document.getElementById('rest-timer-container');
    restTimerContainer.style.display = 'flex';
    
    // Update display
    updateRestTimerDisplay();
    
    // Start the interval
    restTimerInterval = setInterval(function() {
        if (!isRestPaused) {
            restSeconds--;
            updateRestTimerDisplay();
            
            // When timer reaches zero
            if (restSeconds <= 0) {
                clearInterval(restTimerInterval);
                restTimerInterval = null;
                
                // Show notification
                if (Notification.permission === "granted") {
                    new Notification("Rest Timer Complete", {
                        body: `Time to continue your ${exerciseName} sets!`,
                        icon: "/static/img/logo.png"
                    });
                }
                
                // Play sound
                const audio = new Audio('/static/sounds/timer-complete.mp3');
                audio.play().catch(e => console.log('Error playing sound:', e));
                
                // Hide rest timer after short delay
                setTimeout(function() {
                    if (!activeRestTimer) {
                        restTimerContainer.style.display = 'none';
                    }
                }, 3000);
            }
        }
    }, 1000);
    
    // Request notification permission if not already granted
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
  }

  function updateRestTimerDisplay() {
    const minutes = Math.floor(restSeconds / 60);
    const seconds = restSeconds % 60;
    const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    const restTimerElement = document.getElementById('rest-timer');
    restTimerElement.textContent = display;
    restTimerElement.dataset.seconds = restSeconds;
    
    // Update button text based on state
    const pauseButton = document.getElementById('pause-rest');
    pauseButton.textContent = isRestPaused ? 'Resume' : 'Pause';
  }

  function toggleRestTimer() {
    isRestPaused = !isRestPaused;
    
    // Update button text
    const pauseButton = document.getElementById('pause-rest');
    pauseButton.textContent = isRestPaused ? 'Resume' : 'Pause';
  }

  function cancelRestTimer() {
    // Clear interval
    if (restTimerInterval) {
        clearInterval(restTimerInterval);
        restTimerInterval = null;
    }
    
    // Hide rest timer container
    const restTimerContainer = document.getElementById('rest-timer-container');
    restTimerContainer.style.display = 'none';
    
    activeRestTimer = false;
  }

  function restartRestTimer() {
    // If we have a valid total duration, restart the timer
    if (restTotalSeconds > 0) {
        // Clear existing interval
        if (restTimerInterval) {
            clearInterval(restTimerInterval);
        }
        
        // Reset timer variables
        restSeconds = restTotalSeconds;
        isRestPaused = false;
        
        // Update display
        updateRestTimerDisplay();
        
        // Start new interval
        restTimerInterval = setInterval(function() {
            if (!isRestPaused) {
                restSeconds--;
                updateRestTimerDisplay();
                
                if (restSeconds <= 0) {
                    clearInterval(restTimerInterval);
                    restTimerInterval = null;
                }
            }
        }, 1000);
    }
  }

  // Function to update EXP display in the workout stats bar
  function updateExpDisplay() {
    const sessionExpElement = document.getElementById('session-exp');
    if (sessionExpElement) {
        sessionExpElement.textContent = sessionExpGained;
    }
    
    // Update progress bar
    const levelProgressBar = document.getElementById('level-progress');
    if (levelProgressBar) {
        // Get current exp from page data, or default to 0
        const currentExp = parseInt(levelProgressBar.dataset.currentExp || 0);
        const currentLevel = parseInt(levelProgressBar.dataset.currentLevel || 1);
        const expToNextLevel = (currentLevel + 1) * 100;
        
        // Calculate progress percentage
        const totalExp = currentExp + sessionExpGained;
        const levelExp = totalExp % 100;
        const progressPercentage = (levelExp / 100) * 100;
        
        // Update the progress bar
        levelProgressBar.style.width = `${progressPercentage}%`;
        
        // Check if user leveled up
        const startingLevel = Math.floor(currentExp / 100) + 1;
        const newLevel = Math.floor((currentExp + sessionExpGained) / 100) + 1;
        
        if (newLevel > startingLevel) {
            // User leveled up!
            showLevelUpModal(newLevel);
        }
    }
  }

  // Function to show level up modal
  function showLevelUpModal(newLevel) {
    const modal = document.getElementById('levelUpModal');
    if (modal) {
        const levelSpan = document.getElementById('new-level');
        if (levelSpan) {
            levelSpan.textContent = newLevel;
        }
        
        // Show the modal
        $(modal).modal('show');
        
        // Play level up sound if available
        try {
            const audio = new Audio('/static/sounds/level-up.mp3');
            audio.play().catch(e => console.log('Error playing level up sound:', e));
        } catch (e) {
            console.log('Sound not available');
        }
    }
  }

  // Function to show EXP gain notification
  function showExpGain(amount) {
    sessionExpGained += amount;
    
    // Update total EXP display
    updateExpDisplay();
    
    // Show notification
    const notification = document.getElementById('exp-notification');
    if (notification) {
        notification.textContent = `+${amount} EXP`;
        notification.style.display = 'block';
        
        // Add animation class
        notification.classList.add('exp-notification-animate');
        
        // Clear previous timeout if exists
        if (expGainTimeout) {
            clearTimeout(expGainTimeout);
            notification.classList.remove('exp-notification-animate');
            void notification.offsetWidth; // Trigger reflow to restart animation
            notification.classList.add('exp-notification-animate');
        }
        
        // Hide after animation completes
        expGainTimeout = setTimeout(() => {
            notification.style.display = 'none';
            notification.classList.remove('exp-notification-animate');
            expGainTimeout = null;
        }, 3000);
    }
  }

  // Function to calculate EXP gain based on improvement
  function calculateExpGain(exercise, currentSet, previousSet) {
    let expGained = 0;
    const inputType = exercise.input_type;
    
    // Base EXP just for completing a set
    const baseExp = 1;
    expGained += baseExp;
    
    // Calculate volume-based improvements
    if (inputType === 'weight_reps') {
        // Compare current volume with previous
        const currentVolume = (currentSet.weight || 0) * (currentSet.reps || 0);
        const previousVolume = (previousSet.weight || 0) * (previousSet.reps || 0);
        
        if (currentVolume > previousVolume) {
            // Calculate percentage improvement
            const improvement = (currentVolume - previousVolume) / previousVolume;
            // Award EXP based on % improvement (1-10 EXP)
            const volumeExp = Math.min(Math.ceil(improvement * 20), 10);
            expGained += volumeExp;
            
            // Bonus for significant improvements
            if (improvement > 0.2) {
                expGained += 5; // +5 EXP for 20%+ improvement
            }
        }
    } 
    else if (inputType === 'duration') {
        // Compare durations
        const currentDuration = currentSet.time || 0;
        const previousDuration = previousSet.time || 0;
        
        if (currentDuration > previousDuration && previousDuration > 0) {
            // Calculate improvement in seconds
            const improvement = currentDuration - previousDuration;
            // Award 1 EXP per 10% improvement
            const durationExp = Math.ceil((improvement / previousDuration) * 10);
            expGained += Math.min(durationExp, 10);
        }
    }
    else if (inputType === 'distance_duration') {
        // Compare distances and times (better pace)
        const currentDistance = currentSet.distance || 0;
        const previousDistance = previousSet.distance || 0;
        const currentTime = currentSet.time || 1; // Avoid div by zero
        const previousTime = previousSet.time || 1;
        
        // Calculate paces (lower is better)
        const currentPace = currentTime / currentDistance;
        const previousPace = previousTime / previousDistance;
        
        if (currentDistance > previousDistance) {
            // Award EXP for longer distance
            const distanceImprovement = (currentDistance - previousDistance) / previousDistance;
            expGained += Math.min(Math.ceil(distanceImprovement * 10), 8);
        }
        
        if (currentPace < previousPace) {
            // Award EXP for better pace
            const paceImprovement = (previousPace - currentPace) / previousPace;
            expGained += Math.min(Math.ceil(paceImprovement * 15), 7);
        }
    }
    
    // Award bonus EXP for working within or above the target range (if ranges enabled)
    if (exercise.range_enabled) {
        if (inputType.includes('reps') && exercise.max_reps) {
            if (currentSet.reps >= exercise.max_reps) {
                expGained += 3; // Bonus for hitting or exceeding max reps
            } else if (currentSet.reps >= exercise.min_reps) {
                expGained += 1; // Smaller bonus for staying in range
            }
        } else if (inputType.includes('duration') && exercise.max_duration) {
            if (currentSet.time >= exercise.max_duration) {
                expGained += 3; // Bonus for meeting/exceeding max duration
            } else if (currentSet.time >= exercise.min_duration) {
                expGained += 1; // Smaller bonus for staying in range
            }
        } else if (inputType.includes('distance') && exercise.max_distance) {
            if (currentSet.distance >= exercise.max_distance) {
                expGained += 3; // Bonus for meeting/exceeding max distance
            } else if (currentSet.distance >= exercise.min_distance) {
                expGained += 1; // Smaller bonus for staying in range
            }
        }
    }
    
    // Make sure we award some minimum EXP
    return Math.max(expGained, baseExp);
  }

  // Function to reset stats counters
  function resetWorkoutStatsCounters() {
    totalVolume = 0;
    completedSets = 0;
    totalReps = 0;
    
    document.getElementById('workout-volume').textContent = '0';
    document.getElementById('sets-done').textContent = '0';
    document.getElementById('reps-done').textContent = '0';
  }

  // Function to reset performance metrics
  function resetPerformanceMetrics() {
    performanceData = {
      improved: 0,
      declined: 0,
      neutral: 0,
      totalSetsAnalyzed: 0,
      percentChange: 0
    };
    
    const performanceIcon = document.getElementById('performance-icon');
    const performancePercent = document.getElementById('performance-percent');
    
    if (performanceIcon) {
      performanceIcon.textContent = '?';
      performanceIcon.classList.remove('performance-improved', 'performance-declined', 'performance-neutral');
      performanceIcon.classList.add('performance-unknown');
    }
    
    if (performancePercent) {
      performancePercent.textContent = '';
      performancePercent.classList.remove('performance-improved', 'performance-declined', 'performance-neutral');
    }
  }

  // Add DOM content loaded event listener to initialize the workout page
  document.addEventListener('DOMContentLoaded', function() {
    // Initialize progress bar width
    const progressBar = document.getElementById('level-progress');
    if (progressBar) {
      const currentExp = progressBar.getAttribute('data-current-exp');
      if (currentExp) {
        const progressPercentage = currentExp % 100;
        progressBar.style.width = progressPercentage + '%';
      }
    }
    
    // Reset performance metrics to start fresh
    resetPerformanceMetrics();
    
    // Initialize other workout page elements
    // ...
  });

  // Add function to update performance metrics
  function updatePerformanceMetrics(exercise, currentSet, previousSet, isCompleted) {
    // Skip if no previous values to compare against
    if (!previousSet) return;
    
    // Get the input type to determine how to compare
    const inputType = exercise.input_type;
    let isImproved = false;
    let isDeclined = false;
    let percentChange = 0;
    
    // Compare based on exercise type
    if (inputType === 'weight_reps') {
      // For weight/reps, compare total volume (weight × reps)
      const currentVolume = (currentSet.weight || 0) * (currentSet.reps || 0);
      const previousVolume = (previousSet.weight || 0) * (previousSet.reps || 0);
      
      if (previousVolume > 0) {
        percentChange = ((currentVolume - previousVolume) / previousVolume) * 100;
        isImproved = currentVolume > previousVolume;
        isDeclined = currentVolume < previousVolume;
      }
    } 
    else if (inputType === 'weighted_bodyweight' || inputType === 'bodyweight_reps') {
      // For bodyweight exercises, compare reps or (bodyweight + additional weight) × reps
      let currentValue, previousValue;
      
      if (inputType === 'weighted_bodyweight') {
        // For weighted bodyweight, compare (bodyweight + additional weight) × reps
        const additionalWeightCurrent = currentSet.additional_weight || 0;
        const additionalWeightPrevious = previousSet.additional_weight || 0;
        currentValue = (75 + additionalWeightCurrent) * (currentSet.reps || 0);
        previousValue = (75 + additionalWeightPrevious) * (previousSet.reps || 0);
      } else {
        // For bodyweight only, compare reps
        currentValue = currentSet.reps || 0;
        previousValue = previousSet.reps || 0;
      }
      
      if (previousValue > 0) {
        percentChange = ((currentValue - previousValue) / previousValue) * 100;
        isImproved = currentValue > previousValue;
        isDeclined = currentValue < previousValue;
      }
    }
    else if (inputType === 'assisted_bodyweight') {
      // For assisted bodyweight, less assistance is better
      const currentReps = currentSet.reps || 0;
      const previousReps = previousSet.reps || 0;
      const currentAssistance = currentSet.assistance_weight || 0;
      const previousAssistance = previousSet.assistance_weight || 0;
      
      // Calculate an "effective strength" metric
      const currentStrength = currentReps * (75 - currentAssistance);
      const previousStrength = previousReps * (75 - previousAssistance);
      
      if (previousStrength > 0) {
        percentChange = ((currentStrength - previousStrength) / previousStrength) * 100;
        isImproved = currentStrength > previousStrength;
        isDeclined = currentStrength < previousStrength;
      }
    }
    else if (inputType === 'duration') {
      // For duration exercises, longer is better
      const currentDuration = currentSet.time || 0;
      const previousDuration = previousSet.time || 0;
      
      if (previousDuration > 0) {
        percentChange = ((currentDuration - previousDuration) / previousDuration) * 100;
        isImproved = currentDuration > previousDuration;
        isDeclined = currentDuration < previousDuration;
      }
    }
    else if (inputType === 'distance_duration') {
      // For distance/duration, better pace is an improvement
      const currentDistance = currentSet.distance || 0;
      const previousDistance = previousSet.distance || 0;
      const currentTime = currentSet.time || 1; // Avoid div by zero
      const previousTime = previousSet.time || 1;
      
      // Calculate paces (lower is better) in seconds per km
      const currentPace = currentTime / currentDistance;
      const previousPace = previousTime / previousDistance;
      
      if (previousPace > 0 && currentDistance > 0 && previousDistance > 0) {
        percentChange = ((previousPace - currentPace) / previousPace) * 100;
        isImproved = currentPace < previousPace;
        isDeclined = currentPace > previousPace;
      }
    }
    
    // Update our performance tracking
    if (isCompleted) {
      if (isImproved) {
        performanceData.improved++;
        performanceData.percentChange += percentChange;
      } else if (isDeclined) {
        performanceData.declined++;
        performanceData.percentChange += percentChange;
      } else {
        performanceData.neutral++;
      }
      performanceData.totalSetsAnalyzed++;
    } else {
      // Removing a set, so subtract from our totals
      if (isImproved) {
        performanceData.improved--;
        performanceData.percentChange -= percentChange;
      } else if (isDeclined) {
        performanceData.declined--;
        performanceData.percentChange -= percentChange;
      } else {
        performanceData.neutral--;
      }
      performanceData.totalSetsAnalyzed--;
    }
    
    // Update the performance indicator
    updatePerformanceIndicator();
  }

  // Function to update the performance indicator in the UI
  function updatePerformanceIndicator() {
    const performanceIcon = document.getElementById('performance-icon');
    const performancePercent = document.getElementById('performance-percent');
    
    if (!performanceIcon || !performancePercent) return;

    // Reset classes first
    performanceIcon.classList.remove('performance-improved', 'performance-declined', 'performance-neutral', 'performance-unknown');
    
    // If we don't have enough data yet
    if (performanceData.totalSetsAnalyzed < 2) {
      performanceIcon.textContent = '?';
      performanceIcon.classList.add('performance-unknown');
      performancePercent.textContent = '';
      return;
    }
    
    // Calculate the average percent change
    let avgPercentChange = 0;
    if (performanceData.totalSetsAnalyzed > 0) {
      avgPercentChange = performanceData.percentChange / performanceData.totalSetsAnalyzed;
    }
    
    // Format the percent change
    const percentText = avgPercentChange !== 0 ? 
      `${Math.abs(Math.round(avgPercentChange))}%` : '';
    
    // Determine if overall performance is improved or declined
    if (performanceData.improved > performanceData.declined) {
      performanceIcon.textContent = '↑';
      performanceIcon.classList.add('performance-improved');
      performancePercent.textContent = percentText;
      performancePercent.classList.add('performance-improved');
    } else if (performanceData.declined > performanceData.improved) {
      performanceIcon.textContent = '↓';
      performanceIcon.classList.add('performance-declined');
      performancePercent.textContent = percentText;
      performancePercent.classList.add('performance-declined');
    } else {
      performanceIcon.textContent = '→';
      performanceIcon.classList.add('performance-neutral');
      performancePercent.textContent = percentText;
      performancePercent.classList.add('performance-neutral');
    }
  }