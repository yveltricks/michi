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
    console.log(`Fetching details for exercise ID: ${exerciseId}, Name: ${exerciseName}`);
    
    fetch(`/workout/api/exercise-details/${exerciseId}`)
      .then(response => {
          console.log(`Response status for exercise ${exerciseId}:`, response.status);
          
          if (!response.ok) {
              return response.text().then(text => {
                  console.error(`Server error response for exercise ${exerciseId}:`, text);
                  throw new Error(`Server responded with status: ${response.status}`);
              });
          }
          return response.json();
      })
      .then(data => {
            console.log(`Exercise details for ${exerciseName}:`, data);
            
            // Check if there was an error in the response
            if (data.error) {
                console.error(`API returned error for exercise ${exerciseId}:`, data.error);
                throw new Error(data.error);
            }
            
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
            console.error(`Error adding exercise ${exerciseId} - ${exerciseName}:`, error);
            alert(`Error adding exercise: ${error.message}. Please try again.`);
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
    // Check if the modal exists
    const modal = document.getElementById('set-type-modal');
    const setTypeList = document.getElementById('set-type-list');
    
    if (!modal || !setTypeList) {
        console.error('Set type modal elements not found');
        return;
    }
    
    // Store the current selection indices as a global variable
    window.currentSetTypeSelection = {
        exerciseIndex: exerciseIndex,
        setIndex: setIndex
    };
    
    // Clear existing options
    setTypeList.innerHTML = '';
    
    // Create options for each set type
    for (const type in SET_TYPES) {
        const option = document.createElement('div');
        option.className = 'set-type-option';
        option.dataset.type = type;
        
        option.innerHTML = `
            <div class="set-type-info">
                <h4 style="color: ${SET_TYPES[type].color}">${SET_TYPES[type].displayName}${SET_TYPES[type].label}</h4>
                <small>Click to select this set type</small>
            </div>
            <button class="select-btn">Select</button>
        `;
        
        setTypeList.appendChild(option);
    }
    
    // Show the modal
    modal.style.display = 'block';
    
    console.log(`Showing set type modal for exercise ${exerciseIndex}, set ${setIndex}`);
  }
  
  function updateSetType(exerciseIndex, setIndex, setType) {
    console.log(`Updating set type for exercise ${exerciseIndex}, set ${setIndex} to ${setType}`);
    
    // Validate indices
    if (exerciseIndex < 0 || exerciseIndex >= workoutData.exercises.length) {
        console.error('Invalid exercise index');
        return;
    }
    
    const exercise = workoutData.exercises[exerciseIndex];
    if (setIndex < 0 || setIndex >= exercise.sets.length) {
        console.error('Invalid set index');
        return;
    }
    
    // Update the set type
    exercise.sets[setIndex].set_type = setType;
    
    // Re-render the exercises to reflect the change
    renderExercises();
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

    // Add appropriate range inputs based on exercise type
    switch (exercise.input_type) {
        case 'weight_reps':
            // For weight exercises, we set rep ranges
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
            break;

        case 'bodyweight_reps':
        case 'weighted_bodyweight':
        case 'assisted_bodyweight':
            // For all bodyweight variations, we set rep ranges
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
            break;

        case 'duration':
        case 'duration_weight':
            // For duration exercises (like planks), we set time ranges
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
            break;

        case 'distance_duration':
            // For distance/duration exercises (like running), we set both distance and time ranges
            const minDurFormatted = exercise.min_duration ? formatTime(exercise.min_duration) : '';
            const maxDurFormatted = exercise.max_duration ? formatTime(exercise.max_duration) : '';
            
            rangeInputs.innerHTML += `
                <div class="range-input-group">
                    <label>Min Distance (km):</label>
                    <input type="number" id="min-distance" value="${exercise.min_distance || ''}" min="0" step="0.01">
                </div>
                <div class="range-input-group">
                    <label>Max Distance (km):</label>
                    <input type="number" id="max-distance" value="${exercise.max_distance || ''}" min="0" step="0.01">
                </div>
                <div class="range-input-group">
                    <label>Min Duration:</label>
                    <input type="text" id="min-duration" value="${minDurFormatted}" 
                           placeholder="hh:mm:ss" class="time-input" pattern="[0-9:]*"
                           oninput="handleRangeTimeInput(this, 'min')"
                           onkeydown="handleTimeKeyDown(this, event)">
                    <input type="hidden" id="min-duration-seconds" value="${exercise.min_duration || ''}">
                </div>
                <div class="range-input-group">
                    <label>Max Duration:</label>
                    <input type="text" id="max-duration" value="${maxDurFormatted}" 
                           placeholder="hh:mm:ss" class="time-input" pattern="[0-9:]*"
                           oninput="handleRangeTimeInput(this, 'max')"
                           onkeydown="handleTimeKeyDown(this, event)">
                    <input type="hidden" id="max-duration-seconds" value="${exercise.max_duration || ''}">
                </div>
            `;
            break;

        case 'weight_distance':
            // For weight/distance exercises, we set distance ranges
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
            break;
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
    
    // Highlight recently used exercises
    highlightRecentExercises();
  });
  
  // Function to highlight recently used exercises
  function highlightRecentExercises() {
    const exerciseOptions = document.querySelectorAll('.exercise-option');
    
    // Add special styling to recently used exercises
    exerciseOptions.forEach((option, index) => {
        // First 10 exercises are recent if they were sorted on the server
        if (index < 10) {
            option.classList.add('recent-exercise');
            
            // Add a "Recently used" badge
            const infoDiv = option.querySelector('.exercise-info');
            if (infoDiv) {
                const badge = document.createElement('span');
                badge.className = 'recent-badge';
                badge.textContent = 'Recently used';
                infoDiv.appendChild(badge);
            }
        }
    });
    
    // Add CSS for the highlighting
    const style = document.createElement('style');
    style.textContent = `
        .recent-exercise {
            background-color: #f0f8ff; /* Light blue background */
            border-left: 3px solid #4285f4; /* Blue left border */
        }
        .recent-badge {
            font-size: 0.75rem;
            color: white;
            background-color: #4285f4;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 8px;
            display: inline-block;
        }
    `;
    document.head.appendChild(style);
  }
  
  // Handle form submission
  function completeWorkout() {
    // Validate workout has at least one exercise with one completed set
    const hasCompletedSets = workoutData.exercises.some(exercise => 
        exercise.sets && exercise.sets.some(set => set.completed)
    );
    
    if (workoutData.exercises.length === 0) {
        alert('Please add at least one exercise to your workout.');
        return;
    }
  
    if (!hasCompletedSets) {
        alert('Please complete at least one set before finishing your workout.');
        return;
    }
  
    // Prepare workout data
    const title = document.getElementById('workout-title').value;
    const description = document.getElementById('workout-description').value;
    const rating = document.getElementById('workout-rating').value;
    
    // Use the shared workout handler to save the workout
    const success = workoutHandlers.saveWorkout(
        workoutData, 
        title, 
        description, 
        rating, 
        null, // No routine_id for empty workouts
        { 
            volume: parseInt(document.getElementById('workout-volume').textContent), 
            totalSets: parseInt(document.getElementById('sets-done').textContent), 
            totalReps: parseInt(document.getElementById('reps-done').textContent) 
        },
        function(data) {
            // Success callback
            if (data.redirect_url) {
                // Use the redirect URL provided by the server
                console.log(`Redirecting to: ${data.redirect_url}`);
                window.location.href = data.redirect_url;
            } else if (data.session_id && data.session_id !== 'null') {
                // Fallback to using session_id if redirect_url is not available
                console.log(`Redirecting to session: ${data.session_id}`);
                window.location.href = '/workout/session/' + data.session_id;
            } else {
                // If neither redirect_url nor session_id is available, go to workout page
                console.log('No redirect information available, going to workout page');
                window.location.href = '/workout/workout';
            }
        },
        function(error) {
            // Error callback
            alert('Error saving workout: ' + error);
            document.querySelector('.finish-workout-btn').disabled = false;
            document.querySelector('.finish-workout-btn').textContent = 'Complete Workout';
        }
    );
    
    // If validation failed, don't disable the button
    if (success) {
        // Disable button to prevent multiple submissions
        document.querySelector('.finish-workout-btn').disabled = true;
        document.querySelector('.finish-workout-btn').textContent = 'Saving...';
    }
}
  
  // Calculate workout duration
  function calculateWorkoutDuration() {
    // Get timer duration in seconds
    const timerDurationSeconds = getWorkoutDuration();
    
    // Find the longest exercise duration in seconds from completed sets only
    let maxExerciseDurationSeconds = 0;
    workoutData.exercises.forEach(exercise => {
        exercise.sets.forEach(set => {
            if (set.completed && set.time && set.time > maxExerciseDurationSeconds) {
                maxExerciseDurationSeconds = set.time;
            }
        });
    });
    
    console.log('Timer duration (s):', timerDurationSeconds, 'Longest exercise (s):', maxExerciseDurationSeconds);
    
    // Use the maximum between timer and longest completed exercise duration
    const maxDurationSeconds = Math.max(timerDurationSeconds, maxExerciseDurationSeconds);
    
    // Return the duration in seconds (not minutes anymore)
    return maxDurationSeconds;
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
    const value = input.value.replace(/[^0-9]/g, '');
    let formattedValue = '00:00:00';
    let totalSeconds = 0;
    
    if (value.length > 0) {
        // Calculate seconds, minutes, hours from right to left
        const len = value.length;
        
        // Right-align the digits (for values like seconds, minutes, hours)
        let seconds = 0, minutes = 0, hours = 0;
        
        // Process from right to left (least significant to most significant)
        if (len >= 1) seconds += parseInt(value.charAt(len-1));  // 1s place
        if (len >= 2) seconds += parseInt(value.charAt(len-2)) * 10;  // 10s place
        
        if (len >= 3) minutes += parseInt(value.charAt(len-3));  // 1s place
        if (len >= 4) minutes += parseInt(value.charAt(len-4)) * 10;  // 10s place
        
        if (len >= 5) hours += parseInt(value.charAt(len-5));  // 1s place
        if (len >= 6) hours += parseInt(value.charAt(len-6)) * 10;  // 10s place
        
        formattedValue = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        totalSeconds = hours * 3600 + minutes * 60 + seconds;
    }
    
    // Update the input value
    input.value = formattedValue;
    
    // Update data model
    workoutData.exercises[exerciseIndex].sets[setIndex][field] = totalSeconds;
  }

  // Function to synchronize the workout timer with the longest exercise duration
  function syncWorkoutTimer() {
    // We no longer automatically sync the timer with exercise durations
    // This function is now only used when completing the workout
        return;
    }
  
  // Function to calculate recommended values based on previous performance
  function calculateRecommendedValues(exerciseData, previousSets) {
    // Use the shared function if available
    if (typeof workoutHandlers !== 'undefined' && workoutHandlers.calculateRecommendedValues) {
        return workoutHandlers.calculateRecommendedValues(exerciseData, previousSets);
    }
    
    // Fallback to original implementation if shared function not available
    if (!exerciseData.range_enabled || !previousSets || previousSets.length === 0) {
        return null;
    }
    
    // Get the last few completed sets
    const recentSets = previousSets.filter(set => set.completed).slice(-3);
    if (!recentSets.length) {
        return null;
    }
    
    const result = {
        isRecommended: {}
    };
    
    // Check if all sets were at the upper range
    let allAtUpperRange = true;
    let allAtLowerRange = true;
    
    for (const set of recentSets) {
        if (exerciseData.input_type.includes('reps')) {
            if (exerciseData.max_reps && set.reps < exerciseData.max_reps) {
                allAtUpperRange = false;
            }
            if (exerciseData.min_reps && set.reps > exerciseData.min_reps) {
                allAtLowerRange = false;
            }
        } else if (exerciseData.input_type.includes('duration')) {
            if (exerciseData.max_duration && set.time < exerciseData.max_duration) {
                allAtUpperRange = false;
            }
            if (exerciseData.min_duration && set.time > exerciseData.min_duration) {
                allAtLowerRange = false;
            }
        } else if (exerciseData.input_type.includes('distance')) {
            if (exerciseData.max_distance && set.distance < exerciseData.max_distance) {
                allAtUpperRange = false;
            }
            if (exerciseData.min_distance && set.distance > exerciseData.min_distance) {
                allAtLowerRange = false;
            }
        }
    }
    
    // Handle weight-based exercises
    if (['weight_reps', 'weighted_bodyweight', 'duration_weight', 'weight_distance'].includes(exerciseData.input_type)) {
        const lastSet = recentSets[recentSets.length - 1];
        
        if (lastSet && lastSet.weight) {
            let weight = parseFloat(lastSet.weight);
            
            if (allAtUpperRange) {
                // Increase weight by 2.5kg
                weight += 2.5;
                result.isRecommended.weight = true;
            } else if (allAtLowerRange) {
                // Decrease weight by 2.5kg if consistently at lower range
                weight = Math.max(0, weight - 2.5);
                result.isRecommended.weight = true;
            }
            
            result.weight = weight;
        }
    }
    
    return result;
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
    const completedSetsCount = document.getElementById('sets-done');
    const completedRepsCount = document.getElementById('reps-done');
    const totalVolumeElement = document.getElementById('workout-volume');
    
    // Get user weight from data attribute if available
    const userWeight = totalVolumeElement && totalVolumeElement.dataset.userWeight ? 
        parseFloat(totalVolumeElement.dataset.userWeight) : 0;
    
    // Calculate volume based on exercise type and set data
    let setVolume = 0;
    
    if (exercise.input_type === 'weight_reps') {
        setVolume = (set.weight || 0) * (set.reps || 0);
    } else if (exercise.input_type === 'bodyweight_reps') {
        setVolume = userWeight * (set.reps || 0);
    } else if (exercise.input_type === 'weighted_bodyweight') {
        setVolume = (userWeight + (set.additional_weight || 0)) * (set.reps || 0);
    } else if (exercise.input_type === 'assisted_bodyweight') {
        // For assisted, we subtract the assistance from user's weight
        const effectiveWeight = Math.max(0, userWeight - (set.assistance_weight || 0));
        setVolume = effectiveWeight * (set.reps || 0);
    } else if (exercise.input_type === 'duration_weight') {
        // For weighted planks: weight * (duration in seconds / 60)
        // Include both user weight and additional weight if weighted plank
        if (exercise.name && exercise.name.toLowerCase().includes('plank')) {
          const totalWeight = (set.weight || 0) + userWeight;
          setVolume = totalWeight * ((set.time || 0) / 60);
          
          // Store both values in the set data
          set.userWeight = userWeight; 
          console.log(`DEBUG: Weighted plank with user weight ${userWeight}kg, plate ${set.weight}kg, time ${set.time}s, volume ${setVolume}`);
        } else {
          setVolume = (set.weight || 0) * ((set.time || 0) / 60);
        }
    } else if (exercise.input_type === 'weight_distance') {
        setVolume = (set.weight || 0) * (set.distance || 0);
    }
    
    if (isCompleted) {
        // Calculate EXP only if we haven't already for this set
        if (!set.expGained) {
            if (set.hasPrevious && set.prevValues) {
                set.expGained = calculateExpGain(exercise, set, set.prevValues);
            } else {
                // Base EXP for a set without previous values
                set.expGained = 1;
            }
        }
        
        // Increment stats
        completedSetsCount.textContent = (parseInt(completedSetsCount.textContent) || 0) + 1;
        
        if (set.reps) {
            completedRepsCount.textContent = (parseInt(completedRepsCount.textContent) || 0) + parseInt(set.reps);
        }
        
        if (setVolume > 0) {
            const currentVolume = parseInt(totalVolumeElement.textContent) || 0;
            totalVolumeElement.textContent = currentVolume + setVolume;
        }
        
        // Add EXP
        sessionExpGained += set.expGained;
        
        // Show EXP gain notification
        showExpGain(set.expGained);
    } else {
        // Decrement stats
        completedSetsCount.textContent = Math.max(0, (parseInt(completedSetsCount.textContent) || 0) - 1);
        
        if (set.reps) {
            completedRepsCount.textContent = Math.max(0, (parseInt(completedRepsCount.textContent) || 0) - parseInt(set.reps));
        }
        
        if (setVolume > 0) {
            const currentVolume = parseInt(totalVolumeElement.textContent) || 0;
            totalVolumeElement.textContent = Math.max(0, currentVolume - setVolume);
        }
        
        // Remove the exact same amount of EXP that was added
        if (set.expGained) {
            sessionExpGained = Math.max(0, sessionExpGained - set.expGained);
            // Clear the stored EXP so it will be recalculated if completed again
            delete set.expGained;
        }
    }
    
    // Update EXP display
    updateExpDisplay();
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
            // User leveled up! - But we don't show modal anymore
            console.log("User leveled up to level " + newLevel + " (modal disabled)");
        }
    }
  }

  // Function to show EXP gain notification
  function showExpGain(amount) {
    // Only show the notification, don't modify sessionExpGained here
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

  // Add handling for adding an exercise to the workout
  function addExerciseToWorkout(exercise) {
    if (!exercise) return;
    
    // Create a default set based on the exercise type
    let defaultSet = {
      completed: false,
      set_type: 'normal'
    };
    
    // Set appropriate default values based on exercise type
    if (exercise.input_type === 'weight_reps') {
      defaultSet.weight = '';
      defaultSet.reps = '';
    } else if (exercise.input_type === 'bodyweight_reps') {
      defaultSet.reps = '';
    } else if (exercise.input_type === 'duration') {
      defaultSet.time = '';
    } else if (exercise.input_type === 'distance_duration') {
      defaultSet.distance = '';
      defaultSet.time = '';
    } else if (exercise.input_type === 'weighted_bodyweight') {
      defaultSet.additional_weight = '';
      defaultSet.reps = '';
    } else if (exercise.input_type === 'assisted_bodyweight') {
      defaultSet.assistance_weight = '';
      defaultSet.reps = '';
    } else if (exercise.input_type === 'duration_weight') {
      defaultSet.weight = '';
      defaultSet.time = '';
      
      // Special handling for weighted planks - pre-set duration values
      if (exercise.name && exercise.name.toLowerCase().includes('plank')) {
        console.log('Setting up default duration for weighted plank');
        defaultSet.time = 60; // Default to 60 seconds
        // Store defaults at the exercise level too
        if (!exercise.defaults) exercise.defaults = {};
        exercise.defaults.time = 60;
      }
    } else if (exercise.input_type === 'weight_distance') {
      defaultSet.weight = '';
      defaultSet.distance = '';
    }
    
    // If the exercise doesn't have sets array, create it
    if (!exercise.sets) {
      exercise.sets = [];
    }
    
    // Add the set to the exercise
    exercise.sets.push(defaultSet);
    
    // Add the exercise to workout data if it's not already there
    if (!workoutData.exercises.find(e => e.id === exercise.id)) {
      workoutData.exercises.push(exercise);
    }
    
    // Update the UI
    renderExercises();
  }