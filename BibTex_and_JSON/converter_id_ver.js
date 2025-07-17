function parseBibContent(content) {
    const entries = content.split(/@/).filter(entry => entry.trim().length > 0);
    const result = {};

    entries.forEach(entry => {
        const [header, ...body] = entry.split('\n').filter(line => line.trim().length > 0);
        const [entry_type, id] = header.split('{').map(item => item.trim().replace(',', ''));

        const entryObject = { entry_type };
        body.forEach(line => {
            const match = line.match(/(\w+)\s*=\s*[{"](.*?)[}"]/);
            if (match) {
                const key = match[1];
                const value = match[2];
                entryObject[key] = value;
            }
        });

        result[id] = entryObject;
    });

    return result;
}

function convertBibToJson() {
    const bibInput = document.getElementById('bibInput').value;
    const jsonOutput = document.getElementById('jsonOutput');

    if (bibInput.trim().length === 0) {
        alert('Please enter BibTeX content');
        return;
    }

    const jsonObject = parseBibContent(bibInput);
    jsonOutput.value = JSON.stringify(jsonObject, null, 2);
}

function convertJsonToBib() {
    const jsonInput = document.getElementById('jsonInput').value;
    const bibOutput = document.getElementById('bibOutput');

    if (jsonInput.trim().length === 0) {
        alert('Please enter JSON content');
        return;
    }

    try {
        const jsonObject = JSON.parse(jsonInput);
        let bibContent = '';

        for (const id in jsonObject) {
            const entry = jsonObject[id];
            const entry_type = entry.entry_type;
            delete entry.entry_type;
            let entryContent = `@${entry_type}{${id},\n`;

            for (const key in entry) {
                entryContent += `  ${key} = {${entry[key]}},\n`;
            }

            entryContent = entryContent.trim().replace(/,$/, '') + '\n}\n\n';
            bibContent += entryContent;
        }

        bibOutput.value = bibContent.trim();
    } catch (e) {
        alert('Invalid JSON content');
    }
}

function downloadJson() {
    const jsonOutput = document.getElementById('jsonOutput').value;
    const blob = new Blob([jsonOutput], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'output.json';
    a.click();
    URL.revokeObjectURL(url);
}

function downloadBib() {
    const bibOutput = document.getElementById('bibOutput').value;
    const blob = new Blob([bibOutput], { type: 'application/x-bibtex' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
}

function copyJson() {
    const jsonOutput = document.getElementById('jsonOutput');
    jsonOutput.select();
    document.execCommand('copy');
    alert('JSON content copied to clipboard');
}

function copyBib() {
    const bibOutput = document.getElementById('bibOutput');
    bibOutput.select();
    document.execCommand('copy');
    alert('BibTeX content copied to clipboard');
}


function mergeJson() {
    const jsonInput1 = document.getElementById('jsonInput1').value;
    const jsonInput2 = document.getElementById('jsonInput2').value;
    const mergedJsonOutput = document.getElementById('mergedJsonOutput');

    if (jsonInput1.trim().length === 0 || jsonInput2.trim().length === 0) {
        alert('Please enter both JSON contents');
        return;
    }

    try {
        const jsonObject1 = JSON.parse(jsonInput1);
        const jsonObject2 = JSON.parse(jsonInput2);
        const mergedObject = { ...jsonObject1 };

        for (const id in jsonObject2) {
            if (mergedObject[id]) {
                const obj1 = mergedObject[id];
                const obj2 = jsonObject2[id];

                if (JSON.stringify(obj1) === JSON.stringify(obj2)) {
                    continue;
                }

                let newId = `${id}_1`;
                while (mergedObject[newId]) {
                    newId = `${newId}_1`;
                }

                mergedObject[newId] = obj2;
            } else {
                mergedObject[id] = jsonObject2[id];
            }
        }

        const sortedEntries = Object.entries(mergedObject).sort((a, b) => {
            const authorA = a[1].author || '';
            const authorB = b[1].author || '';
            if (authorA === authorB) {
                return a[0].localeCompare(b[0]);
            }
            return authorA.localeCompare(authorB);
        });

        const sortedMergedObject = Object.fromEntries(sortedEntries);

        mergedJsonOutput.value = JSON.stringify(sortedMergedObject, null, 2);
    } catch (e) {
        alert('Invalid JSON content');
    }
}

function downloadMergedJson() {
    const mergedJsonOutput = document.getElementById('mergedJsonOutput').value;
    const blob = new Blob([mergedJsonOutput], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'merged_output.json';
    a.click();
    URL.revokeObjectURL(url);
}

function copyMergedJson() {
    const mergedJsonOutput = document.getElementById('mergedJsonOutput');
    mergedJsonOutput.select();
    document.execCommand('copy');
    alert('Merged JSON content copied to clipboard');
}