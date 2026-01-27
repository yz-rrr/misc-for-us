"""
Test Cases and Usage Examples for the Collostructional Analysis Methods

This file serves dual purposes:
1. Validation tests against Gries's v4.1 results
    * To run these tests, you must place the sample input/output files 
      (e.g., 1.csv, 1_out.csv, 2a.csv, etc.) in the same directory.
    * These files are available at the official website of Stefan Th. Gries:
      https://www.stgries.info/teaching/groningen/
2. Usage examples for different analysis types

See the test cases below for practical usage patterns.

IMPORTANT IMPLEMENTATION NOTES:

1. Log Odds Ratio Calculation:
   This script directly computes Log Odds Ratio based on the 2×2 contingency
   table definition: log((ad)/(bc)). Under this definition, Log Odds Ratio
   theoretically diverges in cases of perfect separation (b=0 or c=0).
   Prior research R implementations use glm(family = binomial), which may
   stop at finite values due to IRLS numerical convergence limits even
   when perfect separation occurs.

2. LLR (Log-Likelihood Ratio) Sign Convention:
   By default, this script returns absolute values for 
   Log-Likelihood Ratio (LLR) and Fisher-Yates Exact test strength (FYE).
   Update (v1.1): Signed Metrics Mode You can optionally enable signed output by 
   setting signed_metrics=True when calling the run() method.
   If enabled, both LLR and FYE will return negative values for repulsion patterns.
"""

import numpy as np
import pandas as pd
from collostructional_analysis import CollostructionalAnalysisMain


class CollostructionalAnalysisTester:
    """Test class for result verification"""
    
    def __init__(self, atol=1e-5, rtol=1e-3):
        """
        Args:
            atol: Absolute tolerance for numerical comparisons
            rtol: Relative tolerance for numerical comparisons
        """
        self.atol = atol
        self.rtol = rtol

    def compare(
        self, 
        result_df: pd.DataFrame, 
        expected_df: pd.DataFrame,
        key_col: str,
        col_mapping: dict = None,
        exclude_cols: list = None,
        join_on: list = None
    ) -> bool:
        """
        Compare results with expected values
        
        Args:
            result_df: Actual results
            expected_df: Expected values
            key_col: Key column name(s)
            col_mapping: Column name mapping dictionary
            exclude_cols: List of columns to exclude from comparison
            join_on: List of join keys for filtering
            
        Returns:
            bool: Comparison result (True: success, False: failure)
        """
        print("\n--- Verifying Results ---")

        # 1. Column alignment
        res = result_df.copy()
        if col_mapping:
            res = res.rename(columns=col_mapping)
        expected = expected_df.copy()

        # 2. Row filtering (Inner Join if requested)
        if join_on:
            print(f"  [Info] Filtering expected data by joining on "
                  f"{join_on}...")
            expected = pd.merge(
                res[join_on].drop_duplicates(), 
                expected, 
                on=join_on, 
                how='inner'
            )

        # 3. Row alignment (Sort)
        sort_keys = key_col if isinstance(key_col, list) else [key_col]
        res = res.sort_values(sort_keys).reset_index(drop=True)
        expected = expected.sort_values(sort_keys).reset_index(drop=True)

        # 4. Row count check
        print(f"  [Info] Rows to compare: {len(res)} (Result) vs "
              f"{len(expected)} (Expected)")
        if len(res) != len(expected):
            print("  [Error] Row count mismatch. Stopping comparison.")
            return False

        # 5. Column intersection
        if exclude_cols:
            res = res.drop(columns=exclude_cols, errors='ignore')
            expected = expected.drop(columns=exclude_cols, errors='ignore')

        common_cols = [c for c in expected.columns if c in res.columns]

        print("Target Columns:")
        print(common_cols)

        # 6. Value comparison
        total_rows = len(res)
        # Set of row indices with at least one column mismatch
        failed_rows = set()

        all_cols_passed = True

        for col in common_cols:
            r_vals = res[col]
            e_vals = expected[col]

            # Numeric column check
            if (pd.api.types.is_numeric_dtype(r_vals) and 
                pd.api.types.is_numeric_dtype(e_vals)):
                
                r_vals = r_vals.astype(float)
                e_vals = e_vals.astype(float)

                # Special handling for LLR 
                # (Compare absolute values due to Gries's signed LLR)
                if "LLR" in col:
                    # Prior research returns negative values for repulsion,
                    # but this script returns absolute values.
                    # TODO: Address notation or change implementation.
                    is_close = np.isclose(
                        np.abs(r_vals), np.abs(e_vals), 
                        rtol=self.rtol, atol=self.atol, equal_nan=True
                    )
                # Special handling for LogOdds 
                # (Allow Inf vs Finite Large Number)
                elif "LOGODDSRATIO" in col:
                    is_close_std = np.isclose(
                        r_vals, e_vals, rtol=self.rtol, atol=self.atol, 
                        equal_nan=True
                    )
                    # Prior R implementation uses glm(family = binomial),
                    # which may stop at finite values due to IRLS numerical
                    # convergence limits even with perfect separation.
                    # Hence we ignore Inf vs >20 mismatches as guideline.
                    is_inf_match = np.isinf(r_vals) & (np.abs(e_vals) > 20)
                    is_close = is_close_std | is_inf_match
                else:
                    is_close = np.isclose(
                        r_vals, e_vals, rtol=self.rtol, atol=self.atol, 
                        equal_nan=True
                    )

                if not is_close.all():
                    print(f"  [Fail] Numeric Column '{col}' mismatch.")
                    diff_idx = np.where(~is_close)[0]
                    failed_rows.update(diff_idx)

                    # Display details for multiple keys
                    for idx in diff_idx[:3]:
                        if isinstance(key_col, list):
                            # Get all key column values and stringify
                            k_vals = res.iloc[idx][key_col].to_dict()
                            k_str = ", ".join([
                                f"{k}={v}" for k, v in k_vals.items()
                            ])
                        else:
                            k_str = f"{key_col}={res.iloc[idx][key_col]}"

                        print(f"    Key [{k_str}]: "
                              f"Res={r_vals.iloc[idx]}, "
                              f"Exp={e_vals.iloc[idx]}")
                    all_cols_passed = False

            # String/Object column check
            else:
                try:
                    r_str = r_vals.astype(str).str.lower().str.strip()
                    e_str = e_vals.astype(str).str.lower().str.strip()
                    is_eq = (r_str == e_str)
                    if not is_eq.all():
                        print(f"  [Fail] String Column '{col}' mismatch.")
                        diff_idx = np.where(~is_eq)[0]
                        failed_rows.update(diff_idx)
                        all_cols_passed = False
                except Exception:
                    if not r_vals.equals(e_vals):
                        print(f"  [Fail] Object Column '{col}' mismatch.")
                        all_cols_passed = False

        # Display success rate
        perfect_rows = total_rows - len(failed_rows)
        success_rate = perfect_rows / total_rows if total_rows > 0 else 0
        print(f"  [Result] {perfect_rows} / {total_rows} rows passed "
              f"perfectly ({success_rate:.1%}).")

        if all_cols_passed:
            print("  >>> TEST PASSED: All checked columns match.")
            return True
        else:
            print("  >>> TEST FAILED: Mismatches found.")
            return False

# ==========================================
# RUNNING THE TESTS
# ==========================================
if __name__ == "__main__":
    tester = CollostructionalAnalysisTester(atol=1e-4, rtol=1e-3)

    # Note: 1_out.csv is missing in user uploads, skipping Test 1 verification against file.
    try:
        print("\n=== CASE 1: Simple (Freq) ===")
        df_in = pd.read_csv("1.csv", sep='\t')
        df_exp = pd.read_csv("1_out.csv", sep='\t')

        res = CollostructionalAnalysisMain.run(df_in, analysis_type=1,
                                               word_col="WORD",
                                               freq_corpus_col="FREQ_WORD_in_CORPUS",
                                               freq_const_col="FREQ_WORD_in_DITRANSITIVE",
                                               total_corpus_size=138664)

        # Mapping: My Code -> Gries File
        mapping = {
            "a": "ditransitive",
            "c": "OTHER",
            "Direction": "RELATION"
        }
        # 1_out has KLD columns, make sure they are checked.
        tester.compare(res, df_exp, key_col="WORD", col_mapping=mapping)

    except Exception as e: print(f"Error 2a: {e}")



    # --- TEST 2a: Distinctive (2a.csv) ---
    try:
        print("\n=== CASE 2a: Distinctive (Raw) ===")
        df_in = pd.read_csv("2a.csv", sep='\t')
        df_exp = pd.read_csv("2a_out.csv", sep='\t')

        res = CollostructionalAnalysisMain.run(df_in, analysis_type=2,
                                               word_col="Verb",
                                               construction_col="Construction")

        # Mapping: My Code -> Gries File
        mapping = {
            "Direction": "PREFERENCE",
            "Verb": "WORD",
            "a": "DITRANSITIVE",
            "c": "PREP_DATIVE"
        }
        # 2a_out has KLD columns, make sure they are checked.
        tester.compare(res, df_exp, key_col="WORD",
                       col_mapping=mapping)
    except Exception as e: print(f"Error 2a: {e}")

    # --- TEST 2b: Distinctive (Freq) (2b.csv) ---
    try:
        print("\n=== CASE 2b: Distinctive (Freq) ===")
        df_in = pd.read_csv("2b.csv", sep='\t')
        df_exp = pd.read_csv("2b_out.csv", sep='\t')

        res = CollostructionalAnalysisMain.run(df_in,
                                               analysis_type=2, word_col="VERB")

        mapping = {
            "Direction": "PREFERENCE",
            "PMI": "MI",  # 2b_out uses "MI" header,
            "a": "DITRANSITIVE",
            "c": "PREP_DATIVE",
            "VERB": "WORD"
        }
        # 2b_out does NOT have KLD columns, exclude them to avoid "missing in expected" confusion or check strictness
        # My code produces them, Expected doesn't have them -> Tester ignores extra columns in Result automatically.
        # But wait, logic says "Intersect Columns". So extra columns in Res are ignored. Good.
        tester.compare(res, df_exp, key_col="WORD", col_mapping=mapping)
    except Exception as e: print(f"Error 2b: {e}")

    # --- TEST 2c: Multiple (2c.csv) ---
    try:
        print("\n=== CASE 2c: Multiple ===")
        df_in = pd.read_csv("2c.csv", sep='\t')
        df_exp = pd.read_csv("2c_out.csv", sep='\t')

        res = CollostructionalAnalysisMain.run(df_in, analysis_type=2, word_col="WORD", construction_col="CONSTRUCTION")

        # Column names in 2c_out: COLLOCATE, ...
        # My code outputs COLLOCATE for Multiple analysis.
        tester.compare(res, df_exp, key_col="COLLOCATE")
    except Exception as e: print(f"Error 2c: {e}")

    # --- TEST 3: Co-varying (3.csv) ---
    try:
        print("\n=== CASE 3: Co-varying ===")
        df_in = pd.read_csv("3.csv", sep='\t')
        df_exp = pd.read_csv("3_out.csv", sep='\t')

        # N=200 is inferred so no need to specify
        res = CollostructionalAnalysisMain.run(df_in, analysis_type=3)

        mapping = {
            "Direction": "RELATION"
        }

        # key_col is specified as a list and sorted by the composite key
        # Specify join_on to extract only the pairs in Result from Expected and compare

        tester.compare(
            res, df_exp,
            key_col=["WORD_SLOT1", "WORD_SLOT2"],
            col_mapping=mapping,
            join_on=["WORD_SLOT1", "WORD_SLOT2"]
        )
    except Exception as e: print(f"Error 3: {e}")

    print("\n=== ALL TESTS COMPLETED ===")
