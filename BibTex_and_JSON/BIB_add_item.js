function toggleGroup(groupId) {
    const group = document.getElementById(groupId);
    if (group.style.display === "none" || group.style.display === "") {
        group.style.display = "block";
    } else {
        group.style.display = "none";
    }
}

function escapeString(str) {
    return str.replace(/"/g, '\\"');
}

function createJSON() {
    createJsonAndBib();
}

function createJsonAndBib() {

    // create new JSON and BibTeX item

    const form = document.getElementById("inputForm");
    const elements = form.elements;
    const jsonData = {};

    const entryTypeSelect = document.getElementById("entry_type_select");
    const entryTypeInput = document.getElementById("entry_type_input");

    let titleBracketValue = true;
    try {
        const titleBracket = document.getElementById("title_brace");
        titleBracketValue = titleBracket.checked;
    } catch (e) {
        console.log(e);
    }

    if (entryTypeInput.value) {
        jsonData.entry_type = entryTypeInput.value;
    } else if (entryTypeSelect.value) {
        jsonData.entry_type = entryTypeSelect.value;
    }

    for (let i = 0; i < elements.length; i++) {
        const element = elements[i];
        if (element.type === "text" && element.value && element.id !== "entry_type_input") {
            let value = escapeString(element.value);
            if (element.id === "title") {
                if (titleBracketValue) {
                    value = `{${value}}`;
                } else {
                    value = `${value}`;
                }

            }
            jsonData[element.id] = value;
        }
    }


    const jsonOutput = document.getElementById("newJsonOutput");
    jsonOutput.value = JSON.stringify(jsonData, null, 2);

    // const jsonOuterData = [jsonData];
    const bibOutput = document.getElementById('newBibOutput');

    // jsonOuterDataを使うと新しいものができる。

    try {
        const jsonArray = [jsonData];
        // const jsonInner = JSON.parse(jsonConverted);
        // const jsonArray = [jsonInner];

        console.log(jsonArray);
        let bibContent = '';

        jsonArray.forEach(entry => {
            const { citation_key, entry_type, ...fields } = entry;
            let entryContent = `@${entry_type}{${citation_key},\n`;

            for (const key in fields) {
                entryContent += `  ${key} = {${fields[key]}},\n`;
            }

            entryContent = entryContent.trim().replace(/,$/, '') + '\n}\n\n';
            bibContent += entryContent;
        });

        bibOutput.value = bibContent.trim();
    } catch (e) {
        alert('Invalid JSON content');
    }

}


function convertNewJsonToBib(){
    const jsonConverted = document.getElementById("newJsonOutput").value;
    const bibOutput = document.getElementById('newBibOutput');
    console.log(jsonConverted);

    try {
        const jsonInner = JSON.parse(jsonConverted);
        const jsonArray = [jsonInner];

        console.log(jsonArray);
        let bibContent = '';

        jsonArray.forEach(entry => {
            const { citation_key, entry_type, ...fields } = entry;
            let entryContent = `@${entry_type}{${citation_key},\n`;

            for (const key in fields) {
                entryContent += `  ${key} = {${fields[key]}},\n`;
            }

            entryContent = entryContent.trim().replace(/,$/, '') + '\n}\n\n';
            bibContent += entryContent;
        });

        bibOutput.value = bibContent.trim();
    } catch (e) {
        alert('Invalid JSON content');
    }

}


function copyNewJsonToClipboard() {
    const jsonOutput = document.getElementById("newJsonOutput");
    jsonOutput.select();
    document.execCommand("copy");
    alert("クリップボードにコピーしました");
}


function copyNewBibToClipboard() {
    const jsonOutput = document.getElementById("newBibOutput");
    jsonOutput.select();
    document.execCommand("copy");
    alert("クリップボードにコピーしました");
}
