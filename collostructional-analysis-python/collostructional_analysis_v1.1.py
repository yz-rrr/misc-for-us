"""
Collostructional Analysis for Python

Python Code for comparison with Gries's v4.1 script results.
(https://www.stgries.info/teaching/groningen/)
Supports:
* COLLOCATIONAL / COLLEXEME ANALYSIS
* (MULTIPLE) DISTINCTIVE COLLOCATE / COLLEXEME ANALYSIS
* (ITEM-BASED) CO-VARYING COLLEXEME ANALYSIS


Tested with:
- scipy 1.16.3 
- numpy 2.0.2
- pandas 2.2.2
(Google Colab)

"""

import pandas as pd
import numpy as np
from scipy.stats import hypergeom, logsumexp  # we didn't use fisher_exact
from abc import ABC, abstractmethod


class AssociationStatsKernel:
    """
    Statistics calculation kernel specialized for association measures.
    
    Functions as pure logic without state, returning metrics for 
    contingency table input (a,b,c,d).
    Uses R-compatible fisher_exact_r_style method to resolve 
    potential discrepancies with SciPy versions.
    """

    @classmethod
    def calculate_all_metrics(
        cls, 
        a: int, 
        b: int, 
        c: int, 
        d: int,
        total_corpus_size: int = None,
        label_pos: str = "Attraction",
        label_neg: str = "Repulsion",
        signed_metrics: bool = False  # <--- 変更: signed -> signed_metrics
    ) -> pd.Series:
        """
        Facade method to calculate all metrics and return as Series.
        
        Args:
            a, b, c, d: Contingency table cell values
            total_corpus_size: Total corpus size (uses a+b+c+d if None)
            label_pos, label_neg: Direction labels
            signed_metrics: Whether to return signed metrics (default: False)
        Returns:
            pd.Series containing all calculated metrics
        """
        N = total_corpus_size if total_corpus_size else (a + b + c + d)

        # Basic Expectations & Direction
        expected_a = ((a + c) * (a + b)) / N
        direction = label_pos if a > expected_a else label_neg

        # Individual Metrics Calculations Log Odds
        lo_stats = cls.calc_log_odds_stats(a, b, c, d)
        fisher_stats = cls.calc_fisher_stats(a, b, c, d, N)
        llr = cls.calc_llr(a, b, c, d, N, expected_a)
        pmi = cls.calc_pmi(a, b, c, d, N)
        dp_stats = cls.calc_delta_p(a, b, c, d)
        kld_stats = cls.calc_kld(a, b, c, d, N)

        # Pearson Residual
        pearson = (
            (a - expected_a) / np.sqrt(expected_a) 
            if expected_a > 0 
            else np.nan
        )

        # --- Apply Sign Logic if requested ---
        fye_score = fisher_stats.get("FYE", np.nan)     
        # 変数名も統一して signed_metrics を使用
        if signed_metrics and not (a > expected_a):
            llr = -llr
            if pd.notna(fye_score):
                fye_score = -fye_score
                fisher_stats["FYE"] = fye_score

        # Consolidate results
        results = {
            "Direction": direction,
            "PEARSONRESID": pearson,
            "LLR": llr,
            "PMI": pmi,
            # Debug info
            "a": a, "b": b, "c": c, "d": d
        }
        results.update(lo_stats)
        results.update(fisher_stats)
        results.update(dp_stats)
        results.update(kld_stats)

        return pd.Series(results)

    @staticmethod
    def fisher_exact_r_style(a, b, c, d, mask_method="distance"):
        """
        Calculates Fisher's Exact Test p-value using a distance-from-expectation approach.
        
        This logic mimics specific R implementations (e.g., Gries v4.1 / certain fisher.test configurations)
        where the two-sided p-value is defined by summing probabilities of tables that are 
        as divergent or more divergent from the expected value than the observed table.
        
        Args:
            a, b, c, d: Cell counts of the 2x2 contingency table.
            mask_method (str): Strategy for defining the two-sided rejection region.
                - "probability"  Sums probabilities of all tables
                    where P(table) <= P(observed).
                - "distance" (default): Sums probabilities of all tables where the count deviates from the 
                  expected value as much as or more than the observed count.
                  This method aligns wirh Gries's R Script results in tests (1_out.csv).
        Returns:
            float: Two-sided p-value.
        """
        # Calculate marginal sums and total
        n11, n12, n21, n22 = a, b, c, d
        n1_ = n11 + n12        # Row 1 sum
        n_1 = n11 + n21        # Col 1 sum
        N = n1_ + (n21 + n22)  # Total sum
        
        # Calculate expected value for cell 'a'
        expected = (n1_ * n_1) / N

        # Define the range of all possible values for cell 'a' (x)
        # low = max(0, Row1_Sum + Col1_Sum - Total)
        # high = min(Row1_Sum, Col1_Sum)
        low = max(0, n1_ + n_1 - N)
        high = min(n1_, n_1)
        x = np.arange(low, high + 1)
        
        # Calculate log-probabilities (logPMF) for all possible tables
        all_log_p = hypergeom.logpmf(x, N, n1_, n_1)
        log_p_obs = hypergeom.logpmf(a, N, n1_, n_1)


        if mask_method == "probability":
            # --- Probability-Based Logic ---
            # Sum probabilities of all tables where P(table) <= P(observed)
            epsilon = 1e-7
            threshold = log_p_obs + np.log(1 + epsilon)
            mask_prob = all_log_p <= threshold
            mask = mask_prob

        elif mask_method == "distance":
            
            # --- Distance-Based Logic (The key to matching R) ---
            # Instead of summing probabilities smaller than P(observed), we sum probabilities
            # of events where the distance from the expected value is >= the observed distance.
            #
            # Example: if expected=1.2 and observed=2 (dist=0.8),
            # we include x=2, 3... AND x=0 (since |0 - 1.2| = 1.2 >= 0.8).
        
            obs_distance = abs(a - expected)
            all_distances = np.abs(x - expected)
        
            # Create a mask for values that are "more extreme" based on distance.
            # A small epsilon (1e-12) is used to handle floating-point inaccuracies.
            mask_dist = all_distances >= (obs_distance - 1e-12)
            mask = mask_dist
        
        # Sum the probabilities in log-space to prevent underflow
        log_p_val = logsumexp(all_log_p[mask])
        
        # Convert back to linear space and cap at 1.0
        p_val = min(np.exp(log_p_val), 1.0)
        
        return p_val
    
    @staticmethod
    def calc_log_odds_stats(a, b, c, d):
        """Calculate Log Odds Ratio, Standard Error, and 95% Wald CI"""
        # Log Odds calculation
        try:
            numerator = a * d
            denominator = b * c
            if denominator == 0:
                if numerator > 0:
                    log_odds = np.inf
                elif numerator == 0:
                    log_odds = np.nan
                else:
                    log_odds = -np.inf
            elif numerator == 0:
                log_odds = -np.inf
            else:
                log_odds = np.log(numerator / denominator)
        except Exception:
            log_odds = np.nan

        # Standard Error (Wald)
        # Apply Haldane-Anscombe correction (+0.5) for zero frequencies
        if a > 0 and b > 0 and c > 0 and d > 0:
            se = np.sqrt(1/a + 1/b + 1/c + 1/d)
        else:
            se = np.sqrt(
                1/(a+0.5) + 1/(b+0.5) + 1/(c+0.5) + 1/(d+0.5)
            )

        # 95% CI (Z=1.96)
        if np.isfinite(log_odds):
            lower = log_odds - 1.96 * se
            upper = log_odds + 1.96 * se
            crosses_zero = (lower <= 0 <= upper)
        else:
            lower, upper = np.nan, np.nan
            crosses_zero = False  # or NaN

        return {
            "LOGODDSRATIO": log_odds,
            "LogOdds_SE": se,
            "LogOdds_CI_Lower": lower,
            "LogOdds_CI_Upper": upper,
            "LogOdds_CrossesZero": crosses_zero
        }

    @staticmethod
    def calc_fisher_stats(a, b, c, d, N):
        """Calculate Fisher-Yates Exact Test & Strength (-log10 p)"""
        try:
            # Use R-compatible implementation to resolve discrepancies
            # print("new Fisher")  # Debug line - kept for reference
            # _, p_val = fisher_exact([[a, b], [c, d]])  # SciPy version
            p_val = AssociationStatsKernel.fisher_exact_r_style(a, b, c, d)
            if p_val > 0:
                strength = -np.log10(p_val)
            else:
                print("Underflow in Fisher p-value calculation")
                print(f"p_val={p_val}, a={a}, b={b}, c={c}, d={d}, N={N}")
                # Underflow rescue using direct log calculation
                log_p = hypergeom.logpmf(a, N, a + c, a + b)
                strength = -(log_p / np.log(10))
        except ValueError:
            p_val, strength = np.nan, np.nan

        return {"Fisher_p_value": p_val, "FYE": strength}

    @staticmethod
    def calc_llr(a, b, c, d, N, exp_a):
        """Calculate Log Likelihood Ratio (G2)"""
        def _term(observed, expected):
            return (observed * np.log(observed/expected) 
                    if (observed > 0 and expected > 0) else 0)

        exp_b = ((b + d) * (a + b)) / N
        exp_c = ((a + c) * (c + d)) / N
        exp_d = ((b + d) * (c + d)) / N

        return 2 * (
            _term(a, exp_a) + _term(b, exp_b) +
            _term(c, exp_c) + _term(d, exp_d)
        )

    @staticmethod
    def calc_pmi(a, b, c, d, N):
        """Calculate Pointwise Mutual Information"""
        p_w_c = a / N
        p_w = (a + c) / N
        p_c = (a + b) / N
        
        if p_w_c > 0 and p_w > 0 and p_c > 0:
            return np.log2(p_w_c / (p_w * p_c))
        return -np.inf

    @staticmethod
    def calc_delta_p(a, b, c, d):
        """Calculate Delta P (C2W and W2C)"""
        # C2W: P(W|C) - P(W|!C)
        dp_c2w = (
            (a / (a + b)) - (c / (c + d)) 
            if (a+b) > 0 and (c+d) > 0 
            else np.nan
        )
        
        # W2C: P(C|W) - P(C|!W)
        dp_w2c = (
            (a / (a + c)) - (b / (b + d)) 
            if (a+c) > 0 and (b+d) > 0 
            else np.nan
        )
        
        return {"DELTAPC2W": dp_c2w, "DELTAPW2C": dp_w2c}

    @staticmethod
    def calc_kld(a, b, c, d, N):
        """Calculate Kullback-Leibler Divergence"""
        def _kld_sum(p1, p2, q1, q2):
            val = 0.0
            if p1 > 0:
                if q1 > 0:
                    val += p1 * np.log2(p1/q1)
                else:
                    return np.inf
            if p2 > 0:
                if q2 > 0:
                    val += p2 * np.log2(p2/q2)
                else:
                    return np.inf
            return val

        # KLD C2W
        if (a+b) > 0 and N > 0:
            kld_c2w = _kld_sum(a/(a+b), b/(a+b), (a+c)/N, (b+d)/N)
        else:
            kld_c2w = np.nan

        # KLD W2C
        if (a+c) > 0 and N > 0:
            kld_w2c = _kld_sum(a/(a+c), c/(a+c), (a+b)/N, (c+d)/N)
        else:
            kld_w2c = np.nan

        return {"KLDC2W": kld_c2w, "KLDW2C": kld_w2c}


class CollexemeAnalyzer(ABC):
    """Base class for Collexeme Analysis orchestrators"""
    
    @abstractmethod
    def run(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Abstract method to execute analysis"""
        pass

    def _apply_metrics(self, row, a, b, c, d, N, label_pos, label_neg,
                       signed_metrics: bool = False) -> pd.Series:
        """Helper to call Statistics Kernel"""
        return AssociationStatsKernel.calculate_all_metrics(
            a, b, c, d, 
            total_corpus_size=N, 
            label_pos=label_pos, 
            label_neg=label_neg,
            signed_metrics=signed_metrics
        )


class SimpleCollexemeAnalyzer(CollexemeAnalyzer):
    """Simple Collexeme Analysis implementation"""
    
    def run(
        self, 
        df: pd.DataFrame, 
        word_col: str, 
        freq_corpus_col: str, 
        freq_const_col: str, 
        total_corpus_size: int = None,
        signed_metrics: bool = False
    ) -> pd.DataFrame:
        """Execute Simple Collexeme Analysis"""
        N = (total_corpus_size 
             if total_corpus_size 
             else df[freq_corpus_col].sum())
        C_total = df[freq_const_col].sum()
        print(f"  [Simple] N={N}, C_total={C_total}")

        def _process_row(row):
            a = row[freq_const_col]
            b = C_total - a
            c = row[freq_corpus_col] - a
            d = N - C_total - c
            return self._apply_metrics(
                row, a, b, c, d, N, "Attraction", "Repulsion",
                signed_metrics=signed_metrics
            )

        metrics = df.apply(_process_row, axis=1)
        result = pd.concat([df[word_col], metrics], axis=1)

        # Include CI in Simple analysis display
        target_cols = [
            word_col, "a", "c", "Direction", "LLR", "PEARSONRESID",
            "LOGODDSRATIO", "LogOdds_CI_Lower", "LogOdds_CI_Upper",
            "LogOdds_CrossesZero", "PMI", "DELTAPC2W", "DELTAPW2C", 
            "KLDC2W", "KLDW2C", "FYE"
        ]
        
        result_filtered = result[
            [c for c in target_cols if c in result.columns]
        ]
        return result_filtered.sort_values("FYE", ascending=False, key=abs)


class DistinctiveCollexemeAnalyzer(CollexemeAnalyzer):
    """Distinctive Collexeme Analysis implementation"""
    
    def run(
        self, 
        df: pd.DataFrame, 
        word_col: str, 
        construction_col: str = None, 
        count_cols: list = None, 
        total_corpus_size: int = None,
        signed_metrics: bool = False
    ) -> pd.DataFrame:
        """Execute Distinctive Collexeme Analysis"""
        # Preprocessing (Wide Format conversion)
        if construction_col is not None and construction_col in df.columns:
            counts = df.pivot_table(
                index=word_col, 
                columns=construction_col, 
                aggfunc='size', 
                fill_value=0
            )
        else:
            df_wide = df.copy().set_index(word_col)
            cols_to_use = (
                count_cols 
                if count_cols 
                else df_wide.select_dtypes(include=[np.number]).columns
            )
            counts = df_wide[cols_to_use].fillna(0).astype(int)

        constructions = counts.columns.tolist()
        n_const = len(constructions)
        print(f"  [Distinctive] Constructions: {n_const} {constructions}")

        if n_const == 2:
            return self._handle_two_constructions(
                counts, constructions, word_col, total_corpus_size,
                signed_metrics=signed_metrics
            )
        else:
            # Provides	fast	quick	rapid	swift	SUMABSDEV	LARGESTPREF
            # signed_metrics is not needed for multiple constructions
            return self._handle_multiple_constructions(
                counts, word_col, constructions
            )

    def _handle_two_constructions(
        self, counts, constructions, word_col, total_corpus_size=None,
        signed_metrics: bool = False
    ):
        """Handle standard 2-construction DCA"""
        const_A, const_B = constructions[0], constructions[1]
        total_A, total_B = counts[const_A].sum(), counts[const_B].sum()
        grand_total = (
            total_corpus_size 
            if total_corpus_size 
            else (total_A + total_B)
        )

        def _process_row(row):
            a = row[const_A]
            c = row[const_B]
            b = total_A - a
            d = total_B - c
            return self._apply_metrics(
                row, a, b, c, d, grand_total, const_A, const_B,
                signed_metrics=signed_metrics
            )

        metrics = counts.apply(_process_row, axis=1)
        result = pd.concat([
            counts.reset_index()[word_col], 
            counts.reset_index(drop=True), 
            metrics.reset_index(drop=True)
        ], axis=1)

        # CI typically not displayed in Distinctive analysis 
        # but included in data
        target_cols = (
            [word_col] + constructions + 
            ["Direction", "LLR", "PEARSONRESID", "LOGODDSRATIO",
             "PMI", "DELTAPC2W", "DELTAPW2C", "KLDC2W", "KLDW2C", "FYE"]
        )
        
        result_filtered = result[
            [c for c in target_cols if c in result.columns]
        ]
        return result_filtered.sort_values(
            "LOGODDSRATIO", ascending=False, key=abs
        )

    def _handle_multiple_constructions(self, counts, word_col, constructions):
        """Handle multiple DCA using Pearson Residuals Logic (no Kernel)"""
        obs = counts.values
        row_totals = obs.sum(axis=1)[:, None]
        col_totals = obs.sum(axis=0)[None, :]
        grand_total = obs.sum()
        exp = (row_totals @ col_totals) / grand_total
        
        with np.errstate(divide='ignore', invalid='ignore'):
            residuals = (obs - exp) / np.sqrt(exp)
            residuals = np.nan_to_num(residuals, nan=0.0)
            
        res_df = pd.DataFrame(
            residuals, index=counts.index, columns=counts.columns
        )
        res_df["SUMABSDEV"] = res_df.abs().sum(axis=1)
        res_df["LARGESTPREF"] = res_df[constructions].idxmax(axis=1)
        res_df.reset_index(inplace=True)
        res_df.rename(columns={word_col: "COLLOCATE"}, inplace=True)
        
        return res_df.sort_values("SUMABSDEV", ascending=False)


class CovaryingCollexemeAnalyzer(CollexemeAnalyzer):
    """Co-varying Collexeme Analysis implementation"""
    
    def run(
        self, 
        df: pd.DataFrame, 
        slot1_col: str, 
        slot2_col: str, 
        total_corpus_size: int = None,
        signed_metrics: bool = False
    ) -> pd.DataFrame:
        """Execute Co-varying Collexeme Analysis"""
        pair_counts = (
            df.groupby([slot1_col, slot2_col])
            .size()
            .reset_index(name='a')
        )
        slot1_totals = df[slot1_col].value_counts()
        slot2_totals = df[slot2_col].value_counts()
        N = total_corpus_size if total_corpus_size else len(df)
        print(f"  [Co-varying] N={N}, Pairs={len(pair_counts)}")

        def _process_row(row):
            w1, w2, a = row[slot1_col], row[slot2_col], row['a']
            freq_w1 = slot1_totals.get(w1, 0)
            freq_w2 = slot2_totals.get(w2, 0)
            b = freq_w1 - a
            c = freq_w2 - a
            d = N - (a + b + c)
            return self._apply_metrics(
                row, a, b, c, d, N, "attraction", "repulsion",
                signed_metrics=signed_metrics
            )

        metrics = pair_counts.apply(_process_row, axis=1)
        if 'a' in metrics.columns:
            metrics = metrics.drop(columns=['a'])

        result = pd.concat([pair_counts, metrics], axis=1)
        result["FREQOFSLOT1"] = result["a"] + result["b"]
        result["FREQOFSLOT2"] = result["a"] + result["c"]

        rename_map = {
            "a": "Freq", 
            "Direction": "RELATION", 
            "DELTAPC2W": "DELTAP1TO2", 
            "DELTAPW2C": "DELTAP2TO1", 
            "KLDC2W": "KLD1TO2", 
            "KLDW2C": "KLD2TO1"
        }
        result.rename(columns=rename_map, inplace=True)

        cols = [
            slot1_col, slot2_col, "Freq", "FREQOFSLOT1", "FREQOFSLOT2", 
            "RELATION", "LLR", "LOGODDSRATIO", "PMI", "DELTAP1TO2", 
            "DELTAP2TO1", "KLD1TO2", "KLD2TO1"
        ]
        
        result_filtered = result[
            [c for c in cols if c in result.columns]
        ]
        return result_filtered.sort_values("LLR", ascending=False)


class CollostructionalAnalysisMain:
    """Main interface for Collostructional Analysis"""
    
    @staticmethod
    def run(
        df: pd.DataFrame,
        analysis_type: int,
        # Column specifications
        word_col: str = None,
        freq_corpus_col: str = None,
        freq_const_col: str = None,
        construction_col: str = None,
        count_cols: list = None,
        slot1_col: str = None,
        slot2_col: str = None,
        # Options
        total_corpus_size: int = None,
        signed_metrics: bool = False
    ) -> pd.DataFrame:
        """
        Main entry point for Collostructional Analysis
        
        Args:
            df: Target DataFrame for analysis
            analysis_type: Analysis type (1: Simple, 2: Distinctive, 
                          3: Co-varying)
            Other parameters: Column specifications per analysis type
            
        Returns:
            DataFrame containing analysis results
        """

        def _resolve_col(
            user_input_name: str,
            default_index: int,
            description: str,
            expect_numeric: bool = False
        ) -> str:
            """
            Column name resolution helper.
            
            Uses specified column name if provided, otherwise infers from 
            index. Performs type checking and logging.
            """
            selected_col = None
            method = "Explicit"

            # 1. Use specified column if provided
            if user_input_name:
                if user_input_name not in df.columns:
                    raise ValueError(
                        f"Error: Specified column '{user_input_name}' "
                        f"not found in DataFrame."
                    )
                selected_col = user_input_name

            # 2. Infer from index if no specification
            elif default_index < len(df.columns):
                selected_col = df.columns[default_index]
                method = f"Inferred (Index {default_index})"
            else:
                raise ValueError(
                    f"Error: Could not resolve '{description}'. "
                    f"No name provided and index {default_index} "
                    f"out of bounds."
                )

            # 3. Type check (numeric columns required in some contexts)
            if expect_numeric:
                if not pd.api.types.is_numeric_dtype(df[selected_col]):
                    # Could attempt string-to-number conversion with warning,
                    # but here we use strict error/warning design.
                    raise TypeError(
                        f"Type Mismatch: '{description}' expects numeric "
                        f"column, but resolved to '{selected_col}' "
                        f"({df[selected_col].dtype}). Check input format."
                    )

            # 4. Log output (inform user of inference)
            if method.startswith("Inferred"):
                print(f"  [Info] {description}: {method} "
                      f"-> using column '{selected_col}'")

            return selected_col

        print(f"\n>> CollostructionalAnalysisMain: Running Type "
              f"{analysis_type}")

        # Analysis Type 1: Simple
        if analysis_type == 1:
            # Word column accepts strings, Freq columns require numeric
            w_col = _resolve_col(word_col, 0, "Word Column")
            c_corp = _resolve_col(
                freq_corpus_col, 1, "Freq in Corpus", expect_numeric=True
            )
            c_const = _resolve_col(
                freq_const_col, 2, "Freq in Construction", 
                expect_numeric=True
            )

            analyzer = SimpleCollexemeAnalyzer()
            print("a: Freq in the Construction")
            print("c: Freq not in the Construction")
            
            return analyzer.run(
                df,
                word_col=w_col,
                freq_corpus_col=c_corp,
                freq_const_col=c_const,
                total_corpus_size=total_corpus_size,
                signed_metrics=signed_metrics
            )

        # Analysis Type 2: Distinctive
        elif analysis_type == 2:
            analyzer = DistinctiveCollexemeAnalyzer()

            # Mode determination
            is_raw = False
            if construction_col:
                is_raw = True
            elif count_cols is None:
                # Heuristic: treat as raw if few numeric columns
                if len(df.select_dtypes(include=[np.number]).columns) == 0:
                    is_raw = True

            target_word = _resolve_col(word_col, 0, "Word Column")

            if is_raw:
                print("  [Mode] Raw Token List detected.")
                # In raw mode, 2nd column should be Construction category
                target_const = _resolve_col(
                    construction_col, 1, "Construction Category Column"
                )

                return analyzer.run(
                    df, 
                    word_col=target_word,
                    construction_col=target_const,
                    total_corpus_size=total_corpus_size,
                    signed_metrics=signed_metrics
                )
            else:
                print("  [Mode] Frequency Table detected.")
                return analyzer.run(
                    df, 
                    word_col=target_word,
                    # If count_cols is None, Analyzer will auto-detect 
                    # numeric columns
                    count_cols=count_cols,
                    total_corpus_size=total_corpus_size
                )

        # Analysis Type 3: Co-varying
        elif analysis_type == 3:
            s1 = _resolve_col(slot1_col, 0, "Slot 1 Column")
            s2 = _resolve_col(slot2_col, 1, "Slot 2 Column")

            analyzer = CovaryingCollexemeAnalyzer()
            return analyzer.run(
                df,
                slot1_col=s1,
                slot2_col=s2,
                total_corpus_size=total_corpus_size,
                signed_metrics=signed_metrics
            )

        else:
            raise ValueError(f"Invalid Analysis Type: {analysis_type}")

