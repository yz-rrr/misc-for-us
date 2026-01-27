# Collostructional Analysis for Python

Python implementation for Collostructional Analysis, compatible with Gries's v4.1 script results.

## About this Project

This tool provides a Python-based implementation of Collostructional Analysis, a framework that has evolved significantly over the past two decades.
<!--  (2003-). --> 

## Features

### Core Functionalities

- **Simple Collexeme Analysis**: Analyze word-construction associations
- **Distinctive Collexeme Analysis**: Compare words across constructions
- **Co-varying Collexeme Analysis**: Examine slot-based associations

### Operational Features

- **Pipeline-Friendly Design**: Designed for non-interactive workflows, making it ideal for processing large datasets or integrating into automated data pipelines.
- **Cloud-Ready (Google Colab Optimized)**: Compatible with cloud environments like Google Colaboratory. You can perform complex linguistic analyses directly in your browser without the need for local R installations or manual environment setup.

## Important Implementation Notes

### Fisher-Yates Exact Test Compatibility


The original R script utilizes a custom `fisher.test.mpfr` function. Due to differences in implementation logic, $p$-values may diverge from standard calculation methods, particularly in cases with weak associations (low FYE values).
To address these discrepancies and maintain numerical consistency with reference data (e.g., `1_out.csv`), this script provides the `calculate_fisher_p_custom` method.

**Calculation Methods:** The script supports two strategies for defining the two-sided rejection region. Users can toggle these via the `mask_method` parameter:
* distance (Default): Sums probabilities of all tables where the count deviates from the expected value as much as, or more than, the observed count. This option is intended for compatibility with Gries's original results (e.g. `1_out.csv`).
* probability: Sums probabilities of all tables where $P(table) \le P(observed)$. 
This is intended for compatibility with the standard R fisher.test behavior.


### Log Odds Ratio Calculation
This script directly computes Log Odds Ratio based on the 2×2 contingency table definition: `log((ad)/(bc))`. Under this definition, Log Odds Ratio theoretically diverges in cases of perfect separation (b=0 or c=0). Prior research R implementations use `glm(family = binomial)`, which may stop at finite values due to IRLS numerical convergence limits even when perfect separation occurs.

### Metric Sign Convention (LLR & FYE)

By default, this script returns absolute values for Log-Likelihood Ratio (LLR) and Fisher-Yates Exact test strength (FYE). 

**Update (v1.1)**: Signed Metrics Mode For advanced visualization and simulation, you can enable signed output by setting ```signed_metrics=True```. This will numerically represent Repulsion as negative values.
* If enabled, both LLR and FYE will return negative values for repulsion patterns.
* This mode may be useful for visualization or simulation purposes where the sign is needed to numerically represent the direction of the effect.

## Quick Start

### 1. Simple Analysis (Frequency Data)

Use when you have pre-calculated frequencies:

```python
from collostructional_analysis import CollostructionalAnalysisMain
import pandas as pd

df = pd.read_csv("input.csv")
result = CollostructionalAnalysisMain.run(
    df, 
    analysis_type=1,
    word_col="WORD",
    freq_corpus_col="FREQ_WORD_in_CORPUS", 
    freq_const_col="FREQ_WORD_in_CONSTRUCTION",
    total_corpus_size=138664  # Total corpus size
)
```

**Input format:**
| WORD | FREQ_WORD_in_CORPUS | FREQ_WORD_in_CONSTRUCTION |
|------|--------------------|-----------------------|
| aaa | 1500 | 120 |
| bbb | 890  | 45  |

### 2. Distinctive Analysis (Raw Token Data)

Use when you have individual tokens:

```python
result = CollostructionalAnalysisMain.run(
    df, 
    analysis_type=2,
    word_col="Verb",
    construction_col="Construction"
)
```

**Input format:**
| Verb | Construction |
|------|-------------|
| aaa | ditransitive |
| aaa | prepositional |
| bbb | ditransitive |

### 3. Co-varying Analysis

Use for slot-based analysis:

```python
result = CollostructionalAnalysisMain.run(df, analysis_type=3)
```

**Input format:**
| WORD_SLOT1 | WORD_SLOT2 |
|------------|------------|
| aaa | ccc |
| bbb | ddd |

## Example

```python
import pandas as pd
from collostructional_analysis import CollostructionalAnalysisMain

def run_simple_analysis():
    """Example: Simple Collexeme Analysis"""
    
    # Load your data (comma-separated or tab-separated)
    df = pd.read_csv("input.csv")  # or pd.read_csv("input.csv", sep='\t') for tab-separated data
    
    # Run analysis
    result = CollostructionalAnalysisMain.run(
        df, 
        analysis_type=1,
        word_col="WORD",
        freq_corpus_col="FREQ_WORD_in_CORPUS",
        freq_const_col="FREQ_WORD_in_CONSTRUCTION",
        total_corpus_size=138664  # Your total corpus size
    )
    
    # Save results
    result.to_csv("output.csv", index=False)
    print("Analysis complete! Results saved to output.csv")

if __name__ == "__main__":
    try:
        run_simple_analysis()
    except Exception as e:
        print(f"Error: {e}")
```

## Output Columns

- `Direction`: Attraction/Repulsion tendency
- `LLR`: Log-Likelihood Ratio (absolute values; see implementation notes above)
- `LOGODDSRATIO`: Log Odds Ratio (may show infinity for perfect separation)
- `PMI`: Pointwise Mutual Information. 
    - Note: The column labeled `PMI` in this output corresponds to `MI` in Gries's original scripts.
- `FYE`: Fisher-Yates Exact Test strength
- `PEARSONRESID`: Pearson Residual

Note: Additional columns may be included depending on the analysis mode.

## Data Requirements

### Simple Analysis
- Word frequency in entire corpus
- Word frequency in target construction
- Total corpus size

### Distinctive Analysis
- Either raw tokens or frequency table
- Word identifiers and construction labels

### Co-varying Analysis
- Raw token pairs (slot1, slot2)

## Validation

This implementation has been validated against Gries's R scripts. See `test_for_v4.1.py` for detailed validation examples and usage patterns.

## Requirements

```
pandas>=1.3.0
numpy>=1.21.0
scipy>=1.6.0,<2.0.0
```

## References

Based on "Coll.analysis 4.1" by Stefan Th. Gries.
- Gries, Stefan Th. 2024. Coll.analysis 4.1. A script for R to compute perform collostructional analyses. <https://www.stgries.info/teaching/groningen/index.html>.


## Acknowledgments

I would like to acknowledge Anatol Stefanowitsch, Stefan Th. Gries, and their collaborators for their foundational and pioneering work in collostructural analysis since 2003.

Special thanks are also due to Stefan Th. Gries for the continuous development of the original R scripts, including the latest 2024 update (v4.1), which served as the foundation for this Python implementation.

**Note**: The English documentation was drafted with the assistance of LLMs to ensure clarity. While I have reviewed the content, suggestions for linguistic refinement are highly appreciated.

## License
This project is licensed under the MIT License - see [the LICENSE file](https://opensource.org/licenses/mit-license.php) for details.
Copyright (c) 2026 yz_rrr

