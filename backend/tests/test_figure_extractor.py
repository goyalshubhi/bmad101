import pytest

from app.services.verify.figure_extractor import extract_figures


class TestDollarAmounts:
    def test_simple_dollar(self):
        text = "Revenue was $1,234.56 in Q1."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "$1,234.56" in values

    def test_dollar_with_suffix(self):
        text = "The company earned $5.2M last year."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "$5.2M" in values

    def test_dollar_billions(self):
        text = "Market cap reached $12B."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "$12B" in values

    def test_dollar_thousands(self):
        text = "Average salary is $85K per year."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "$85K" in values

    def test_negative_dollar(self):
        text = "Net loss was -$4.2M for the quarter."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "-$4.2M" in values


class TestPercentages:
    def test_simple_percentage(self):
        text = "Growth was 12.5% over the period."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "12.5%" in values

    def test_decimal_percentage(self):
        text = "Margin improved to 3.14% from 2.71%."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "3.14%" in values
        assert "2.71%" in values

    def test_negative_percentage(self):
        text = "Revenue declined by -3.5% this quarter."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "-3.5%" in values


class TestLargeNumbers:
    def test_large_decimal(self):
        text = "Total units sold: 1234.56 thousand."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "1234.56" in values

    def test_standalone_integer(self):
        text = "There were 5000 transactions recorded."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "5000" in values


class TestExclusionHeuristics:
    def test_years_excluded(self):
        text = "In 2024 the company grew revenue to $500M."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "2024" not in values
        assert "$500M" in values

    def test_recent_years_excluded(self):
        text = "Between 1999 and 2025 we saw growth."
        figures = extract_figures(text)
        values = [f["value"] for f in figures]
        assert "1999" not in values
        assert "2025" not in values


class TestContextSentence:
    def test_extracts_containing_sentence(self):
        text = "Q1 was strong. Revenue reached $500M in the quarter. Q2 lagged."
        figures = extract_figures(text)
        dollar_fig = next(f for f in figures if f["value"] == "$500M")
        assert "Revenue reached $500M in the quarter" in dollar_fig["context_sentence"]

    def test_narrative_position(self):
        text = "Revenue was $100. Cost was $50."
        figures = extract_figures(text)
        positions = [f["narrative_position"] for f in figures]
        assert positions == sorted(positions)


class TestDeduplication:
    def test_same_value_same_sentence_deduped(self):
        text = "Revenue was $100 and $100 in total."
        figures = extract_figures(text)
        dollar_figs = [f for f in figures if f["value"] == "$100"]
        assert len(dollar_figs) == 1

    def test_same_value_different_sentences(self):
        text = "Revenue was $100 in Q1. Costs were also $100 in Q1."
        figures = extract_figures(text)
        dollar_figs = [f for f in figures if f["value"] == "$100"]
        assert len(dollar_figs) == 2


class TestMixedFormats:
    def test_narrative_with_multiple_formats(self):
        text = "Revenue of $1.2M grew 15.3% to reach 50000 units."
        figures = extract_figures(text)
        assert len(figures) >= 2
        values = [f["value"] for f in figures]
        assert "$1.2M" in values
        assert "15.3%" in values
