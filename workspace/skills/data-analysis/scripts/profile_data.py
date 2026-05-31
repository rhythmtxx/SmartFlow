#!/usr/bin/env python3
"""
Data Profile Generator

Quick data quality assessment tool that provides:
- Data dimensions and types
- Missing value analysis
- Duplicate detection
- Outlier identification
- Data type recommendations
- Statistical summary

Usage:
    python profile_data.py <data_file>
"""

import sys
import os
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


def load_data(filepath):
    """Load data from various file formats."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == '.csv':
        df = pd.read_csv(filepath)
    elif ext in ['.xlsx', '.xls']:
        df = pd.read_excel(filepath)
    elif ext == '.json':
        df = pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    
    return df


def detect_outliers_iqr(series):
    """Detect outliers using IQR method."""
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = ((series < lower) | (series > upper)).sum()
    return outliers, lower, upper


def detect_outliers_zscore(series, threshold=3):
    """Detect outliers using Z-score method."""
    z_scores = np.abs(stats.zscore(series.dropna()))
    outliers = (z_scores > threshold).sum()
    return outliers


def suggest_dtype(col):
    """Suggest optimal data type for a column."""
    dtype = str(col.dtype)
    nunique = col.nunique()
    count = len(col)
    
    # Check if can be downcast numeric
    if dtype in ['int64', 'int32']:
        if col.min() >= 0:
            if col.max() < 255:
                return 'uint8 (save memory)'
            elif col.max() < 65535:
                return 'uint16 (save memory)'
        return 'int32 (save memory)'
    
    if dtype == 'float64':
        return 'float32 (save memory)'
    
    # Check if should be categorical
    if dtype == 'object':
        if nunique / count < 0.05 and nunique < 100:
            return 'category (save memory & speed up operations)'
        return 'object (current is fine)'
    
    return dtype


def profile_data(df):
    """Generate comprehensive data profile."""
    profile_results = []
    
    for col in df.columns:
        result = {
            'Column': col,
            'Dtype': str(df[col].dtype),
            'Count': df[col].count(),
            'Missing': df[col].isnull().sum(),
            'Missing %': f"{df[col].isnull().sum() / len(df) * 100:.2f}%",
            'Unique': df[col].nunique(),
            'Unique %': f"{df[col].nunique() / len(df) * 100:.2f}%",
            'Duplicates': df[col].duplicated().sum(),
        }
        
        # Numeric columns
        if df[col].dtype in ['int64', 'int32', 'float64', 'int16', 'float32']:
            result.update({
                'Min': df[col].min(),
                'Max': df[col].max(),
                'Mean': f"{df[col].mean():.2f}",
                'Median': f"{df[col].median():.2f}",
                'Std': f"{df[col].std():.2f}",
                'Skewness': f"{df[col].skew():.2f}",
                'Kurtosis': f"{df[col].kurtosis():.2f}",
            })
            
            # Outlier detection
            outliers_iqr, lower, upper = detect_outliers_iqr(df[col])
            outliers_zscore = detect_outliers_zscore(df[col])
            result.update({
                'Outliers (IQR)': outliers_iqr,
                'IQR Bounds': f"[{lower:.2f}, {upper:.2f}]",
                'Outliers (Z-score)': outliers_zscore,
            })
        
        # Categorical columns
        elif df[col].dtype in ['object', 'category']:
            top_val = df[col].mode()[0] if len(df[col].mode()) > 0 else None
            result.update({
                'Top Value': top_val,
                'Top Freq': df[col].value_counts().iloc[0] if len(df[col].value_counts()) > 0 else 0,
                'Top %': f"{df[col].value_counts().iloc[0] / len(df) * 100:.2f}%" if len(df[col].value_counts()) > 0 else '0%',
            })
        
        # Suggested dtype
        result['Suggested Dtype'] = suggest_dtype(df[col])
        
        profile_results.append(result)
    
    return pd.DataFrame(profile_results)


def print_quality_report(df):
    """Print data quality report."""
    print("\n" + "="*80)
    print("DATA QUALITY REPORT")
    print("="*80 + "\n")
    
    # Basic info
    print("📊 BASIC INFO")
    print("-" * 80)
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Memory Usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    # Missing values
    print("\n❌ MISSING VALUES")
    print("-" * 80)
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({
        'Column': missing.index,
        'Missing': missing.values,
        'Percentage': missing_pct.values
    })
    missing_df = missing_df[missing_df['Missing'] > 0].sort_values('Missing', ascending=False)
    
    if len(missing_df) > 0:
        print(missing_df.to_string(index=False))
    else:
        print("  ✓ No missing values found!")
    
    # Duplicates
    print("\n🔄 DUPLICATES")
    print("-" * 80)
    dup_rows = df.duplicated().sum()
    print(f"  Duplicate rows: {dup_rows} ({dup_rows/len(df)*100:.2f}%)")
    
    if dup_rows > 0:
        print("  Recommendation: Consider removing duplicates")
    
    # Constant columns
    print("\n📏 CONSTANT/NEAR-CONSTANT COLUMNS")
    print("-" * 80)
    constant_cols = []
    near_constant_cols = []
    
    for col in df.columns:
        unique_pct = df[col].nunique() / len(df) * 100
        if unique_pct == 0:
            constant_cols.append((col, 0))
        elif unique_pct < 1:
            top_pct = df[col].value_counts().iloc[0] / len(df) * 100
            near_constant_cols.append((col, top_pct))
    
    if constant_cols:
        print("  Constant columns (no variation):")
        for col, pct in constant_cols:
            print(f"    - {col}")
    
    if near_constant_cols:
        print("  Near-constant columns (>95% same value):")
        for col, pct in near_constant_cols:
            print(f"    - {col} ({pct:.2f}% same value)")
    
    if not constant_cols and not near_constant_cols:
        print("  ✓ No constant or near-constant columns found!")
    
    # High cardinality
    print("\n🎯 HIGH CARDINALITY COLUMNS")
    print("-" * 80)
    high_card = []
    
    for col in df.select_dtypes(include=['object', 'category']).columns:
        unique_pct = df[col].nunique() / len(df) * 100
        if unique_pct > 80:
            high_card.append((col, df[col].nunique(), unique_pct))
    
    if high_card:
        print("  Columns with >80% unique values:")
        for col, nunique, pct in high_card:
            print(f"    - {col}: {nunique} unique values ({pct:.2f}%)")
    else:
        print("  ✓ No high cardinality columns found!")
    
    # Skewed distributions
    print("\n📈 SKEWED DISTRIBUTIONS")
    print("-" * 80)
    skewed_cols = []
    
    for col in df.select_dtypes(include=[np.number]).columns:
        skewness = df[col].skew()
        if abs(skewness) > 1:
            skewed_cols.append((col, skewness))
    
    if skewed_cols:
        print("  Highly skewed columns (|skewness| > 1):")
        for col, skew in sorted(skewed_cols, key=lambda x: abs(x[1]), reverse=True):
            direction = "right" if skew > 0 else "left"
            print(f"    - {col}: {skew:.2f} ({direction}-skewed)")
        print("  Recommendation: Consider log/Box-Cox transformation")
    else:
        print("  ✓ No highly skewed distributions found!")
    
    # Outliers
    print("\n⚠️  OUTLIERS (IQR Method)")
    print("-" * 80)
    outlier_cols = []
    
    for col in df.select_dtypes(include=[np.number]).columns:
        outliers, _, _ = detect_outliers_iqr(df[col])
        if outliers > 0:
            outlier_pct = outliers / len(df) * 100
            outlier_cols.append((col, outliers, outlier_pct))
    
    if outlier_cols:
        outlier_cols.sort(key=lambda x: x[2], reverse=True)
        print("  Columns with outliers:")
        for col, count, pct in outlier_cols:
            print(f"    - {col}: {count} outliers ({pct:.2f}%)")
        print("  Recommendation: Investigate and decide whether to remove, cap, or transform")
    else:
        print("  ✓ No outliers detected!")
    
    print("\n" + "="*80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python profile_data.py <data_file>")
        print("Supported formats: CSV, Excel, JSON")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("DATA PROFILER")
    print("="*80 + "\n")
    
    # Load data
    print("Loading data...")
    df = load_data(filepath)
    print(f"✓ Loaded {len(df):,} rows × {len(df.columns)} columns\n")
    
    # Generate profile
    print("Generating profile...\n")
    profile_df = profile_data(df)
    
    # Print quality report
    print_quality_report(df)
    
    # Print detailed profile
    print("="*80)
    print("DETAILED COLUMN PROFILE")
    print("="*80 + "\n")
    
    # Set display options for better readability
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)
    
    print(profile_df.to_string(index=False))
    
    # Save to file
    output_path = os.path.join(os.path.dirname(filepath), 'data_profile.csv')
    profile_df.to_csv(output_path, index=False)
    print(f"\n✓ Profile saved to: {output_path}")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
