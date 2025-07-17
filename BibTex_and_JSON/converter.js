/* MergeJson 関数は拡張前のもの。 */

function parseBibContent(content) {
    const entries = content.split(/@/).filter(entry => entry.trim().length > 0);
    const result = [];

    entries.forEach(entry => {
        const [header, ...body] = entry.split('\n').filter(line => line.trim().length > 0);
        const [kind, id] = header.split('{').map(item => item.trim().replace(',', ''));

        const entryObject = { citation_key: id, entry_type: kind };
        body.forEach(line => {
            const match = line.match(/(\w+)\s*=\s*[{"](.*?)[}"]/);
            if (match) {
                const key = match[1];
                const value = match[2];
                entryObject[key] = value;
            }
        });

        result.push(entryObject);
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

    const jsonArray = parseBibContent(bibInput);
    jsonOutput.value = JSON.stringify(jsonArray, null, 2);
}

function convertJsonToBib() {
    const jsonInput = document.getElementById('jsonInput').value;
    const bibOutput = document.getElementById('bibOutput');

    if (jsonInput.trim().length === 0) {
        alert('Please enter JSON content');
        return;
    }

    try {
        const jsonArray = JSON.parse(jsonInput);
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
    a.href = url;
    a.download = 'output.bib';
    a.click();
    URL.revokeObjectURL(url);
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


function mergeJsonFromTextarea() {
    const jsonInput1 = document.getElementById('jsonInput1').value;
    const jsonInput2 = document.getElementById('jsonInput2').value;
    const mergedJsonOutput = document.getElementById('mergedJsonOutput');

    if (jsonInput1.trim().length === 0 || jsonInput2.trim().length === 0) {
        alert('Please enter both JSON contents');
        return;
    }

    try {
        const jsonArray1 = JSON.parse(jsonInput1);
        const jsonArray2 = JSON.parse(jsonInput2);
        const mergedArray = mergeJsonArrays(jsonArray1, jsonArray2);

        const sortedEntries = mergedArray.sort((a, b) => {
            const authorA = a.author || '';
            const authorB = b.author || '';
            if (authorA === authorB) {
                return a.citation_key.localeCompare(b.citation_key);
            }
            return authorA.localeCompare(authorB);
        });

        mergedJsonOutput.value = JSON.stringify(sortedEntries, null, 2);
    } catch (e) {
        alert('Invalid JSON content');
    }
}

function mergeJsonArrays(jsonArray1, jsonArray2) {
    // 入力が配列かどうかをチェック
    if (!Array.isArray(jsonArray1) || !Array.isArray(jsonArray2)) {
        throw new Error("Both arguments must be arrays");
    }

    const mergedMap = new Map();
    
    // jsonArray1 を Map に追加
    jsonArray1.forEach(item => {
        if (item.citation_key) {
            mergedMap.set(item.citation_key, item);
        }
    });

    jsonArray2.forEach(entry => {
        const { citation_key } = entry;

        if (mergedMap.has(citation_key)) {
            const existingEntry = mergedMap.get(citation_key);

            if (JSON.stringify(existingEntry) === JSON.stringify(entry)) {
                return;
            }

            let newId = `${citation_key}_1`;
            while (mergedMap.has(newId)) {
                newId = `${newId}_1`;
            }

            mergedMap.set(newId, { ...entry, citation_key: newId });
        } else {
            mergedMap.set(citation_key, entry);
        }
    });

    return Array.from(mergedMap.values());
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
        const jsonArray1 = JSON.parse(jsonInput1);
        const jsonArray2 = JSON.parse(jsonInput2);
        const mergedArray = [...jsonArray1];

        jsonArray2.forEach(entry => {
            const { citation_key } = entry;

            if (mergedArray.some(item => item.citation_key === citation_key)) {
                const existingEntry = mergedArray.find(item => item.citation_key === citation_key);
                if (JSON.stringify(existingEntry) === JSON.stringify(entry)) {
                    return;
                }

                let newId = `${citation_key}_1`;
                while (mergedArray.some(item => item.citation_key === newId)) {
                    newId = `${newId}_1`;
                }

                mergedArray.push({ ...entry, citation_key: newId });
            } else {
                mergedArray.push(entry);
            }
        });

        const sortedEntries = mergedArray.sort((a, b) => {
            const authorA = a.author || '';
            const authorB = b.author || '';
            if (authorA === authorB) {
                return a.citation_key.localeCompare(b.citation_key);
            }
            return authorA.localeCompare(authorB);
        });

        mergedJsonOutput.value = JSON.stringify(sortedEntries, null, 2);
    } catch (e) {
        alert('Invalid JSON content');
    }
}

function convertMergedJsonToBib(jsonArray) {
    // const mergedJsonOutput = document.getElementById('mergedJsonOutput').value;
    const mergedBibOutput = document.getElementById('mergedBibOutput');

    /*
    if (mergedJsonOutput.trim().length === 0) {
        alert('No merged JSON content to convert');
        return;
    }
    */

    try {
        // const jsonArray = JSON.parse(mergedJsonOutput);
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

        mergedBibOutput.value = bibContent.trim();
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

function downloadMergedBib() {
    const mergedBibOutput = document.getElementById('mergedBibOutput').value;
    const blob = new Blob([mergedBibOutput], { type: 'application/x-bibtex' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'merged_output.bib';
    a.click();
    URL.revokeObjectURL(url);
}

function copyMergedBib() {
    const mergedBibOutput = document.getElementById('mergedBibOutput');
    mergedBibOutput.select();
    document.execCommand('copy');
    alert('Merged BibTeX content copied to clipboard');
}

function mergeBib() {
    const bibInput1 = document.getElementById('bibInput1').value;
    const bibInput2 = document.getElementById('bibInput2').value;

    if (bibInput1.trim().length === 0 || bibInput2.trim().length === 0) {
        alert('Please enter both BibTeX contents');
        return;
    }

    const json1 = parseBibContent(bibInput1);
    const json2 = parseBibContent(bibInput2);

    //const jsonInput1 = JSON.stringify(json1);
    //const jsonInput2 = JSON.stringify(json2);

    // alert(jsonInput1);

    // Use mergeJson to merge JSON data
    const mergedArray = mergeJsonArrays(json1, json2);
    // document.getElementById('mergedJsonOutput').value = mergedJsonOutput;

    // Convert merged JSON to BibTeX
    convertMergedJsonToBib(mergedArray);
}

