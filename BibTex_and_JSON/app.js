function readJSON() {
    const jsonInput = document.getElementById('jsonInput').value;
    try {
        const jsonObject = JSON.parse(jsonInput);
        document.getElementById('output').innerText = JSON.stringify(jsonObject, null, 2);
    } catch (e) {
        document.getElementById('output').innerText = 'Invalid JSON';
    }
}

function writeJSON() {
    const jsonObject = {
        name: "John Doe",
        age: 30,
        city: "New York"
    };
    document.getElementById('jsonInput').value = JSON.stringify(jsonObject, null, 2);
}
