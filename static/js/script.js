// AOS Animation
if (typeof AOS !== "undefined") {
    AOS.init({
        duration: 1000,
        once: true
    });
}

// BMI Calculator
function calculateBMI() {

    let weight = document.getElementById("weight").value;
    let height = document.getElementById("height").value / 100;

    if (weight === "" || height === 0) {
        alert("Please enter weight and height");
        return;
    }

    let bmi = weight / (height * height);
    let result = document.getElementById("result");

    if (bmi < 18.5) {
        result.innerHTML = "Underweight : " + bmi.toFixed(1);
    }
    else if (bmi < 25) {
        result.innerHTML = "Normal Weight : " + bmi.toFixed(1);
    }
    else {
        result.innerHTML = "Overweight : " + bmi.toFixed(1);
    }
}