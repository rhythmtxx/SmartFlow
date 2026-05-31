#!/usr/bin/env python3
"""
Automated Data Analysis Script

Generates comprehensive analysis report including:
- Data profile
- Correlation matrix
- Distribution plots
- Statistical summary
- HTML report

Usage:
    python auto_analysis.py <data_file>
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-darkgrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


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
    
    print(f"✓ Loaded {len(df)} rows × {len(df.columns)} columns")
    return df


def generate_data_profile(df):
    """Generate basic data profile."""
    profile = {}
    
    # Basic info
    profile['shape'] = df.shape
    profile['columns'] = list(df.columns)
    profile['dtypes'] = df.dtypes.to_dict()
    
    # Missing values
    profile['missing'] = df.isnull().sum().to_dict()
    profile['missing_pct'] = (df.isnull().sum() / len(df) * 100).to_dict()
    
    # Duplicates
    profile['duplicates'] = df.duplicated().sum()
    
    # Unique values
    profile['nunique'] = df.nunique().to_dict()
    
    return profile


def generate_statistics(df):
    """Generate statistical summary."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    stats = {}
    
    # Numeric statistics
    if len(numeric_cols) > 0:
        stats['numeric'] = df[numeric_cols].describe().to_dict()
        
        # Add skewness and kurtosis
        stats['skewness'] = df[numeric_cols].skew().to_dict()
        stats['kurtosis'] = df[numeric_cols].kurtosis().to_dict()
    
    # Categorical statistics
    if len(categorical_cols) > 0:
        stats['categorical'] = {}
        for col in categorical_cols:
            stats['categorical'][col] = {
                'unique': df[col].nunique(),
                'top': df[col].mode()[0] if len(df[col].mode()) > 0 else None,
                'freq': df[col].value_counts().iloc[0] if len(df[col].value_counts()) > 0 else 0
            }
    
    return stats


def create_correlation_matrix(df, output_path):
    """Create correlation matrix heatmap."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if len(numeric_cols) < 2:
        print("⚠ Not enough numeric columns for correlation matrix")
        return None
    
    corr_matrix = df[numeric_cols].corr()
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                center=0, square=True, linewidths=0.5, ax=ax)
    plt.title('Correlation Matrix', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved correlation matrix: {output_path}")
    return corr_matrix


def create_distribution_plots(df, output_path):
    """Create distribution plots for all numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if len(numeric_cols) == 0:
        print("⚠ No numeric columns for distribution plots")
        return
    
    n_cols = min(4, len(numeric_cols))
    n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
    axes = axes.flatten() if len(numeric_cols) > 1 else [axes]
    
    for idx, col in enumerate(numeric_cols):
        data = df[col].dropna()
        axes[idx].hist(data, bins=30, color='#4ECDC4', alpha=0.7, edgecolor='black')
        axes[idx].set_title(col, fontweight='bold')
        axes[idx].set_xlabel('Value')
        axes[idx].set_ylabel('Frequency')
        axes[idx].grid(True, alpha=0.3)
    
    # Hide empty subplots
    for idx in range(len(numeric_cols), len(axes)):
        axes[idx].set_visible(False)
    
    plt.suptitle('Feature Distributions', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved distribution plots: {output_path}")


def create_categorical_plots(df, output_dir):
    """Create bar charts for categorical columns."""
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    if len(categorical_cols) == 0:
        print("⚠ No categorical columns for bar charts")
        return
    
    for col in categorical_cols:
        value_counts = df[col].value_counts().head(20)  # Top 20 only
        
        if len(value_counts) == 0:
            continue
        
        fig, ax = plt.subplots(figsize=(10, max(6, len(value_counts) * 0.3)))
        
        if len(value_counts) > 10:
            # Horizontal bar for many categories
            value_counts.plot(kind='barh', color='#4ECDC4', ax=ax)
            ax.set_xlabel('Count')
        else:
            # Vertical bar for few categories
            value_counts.plot(kind='bar', color='#4ECDC4', ax=ax)
            ax.set_ylabel('Count')
            plt.xticks(rotation=45, ha='right')
        
        ax.set_title(f'{col} Distribution', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, f'categorical_{col}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    print(f"✓ Saved {len(categorical_cols)} categorical plots")


def generate_html_report(df, profile, stats, output_path):
    """Generate comprehensive HTML report."""
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        h2 {{
            color: #667eea;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        h3 {{
            color: #764ba2;
            margin: 20px 0 10px 0;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 0.9rem;
            color: #6c757d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #667eea;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .image-container {{
            margin: 20px 0;
            text-align: center;
        }}
        img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #6c757d;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>📊 Data Analysis Report</h1>
        <p class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </header>
    
    <div class="container">
        <!-- Executive Summary -->
        <section class="card">
            <h2>Executive Summary</h2>
            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-value">{profile['shape'][0]:,}</div>
                    <div class="metric-label">Total Rows</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{profile['shape'][1]}</div>
                    <div class="metric-label">Features</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{sum(profile['missing'].values())}</div>
                    <div class="metric-label">Missing Values</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{profile['duplicates']}</div>
                    <div class="metric-label">Duplicates</div>
                </div>
            </div>
        </section>
        
        <!-- Data Quality -->
        <section class="card">
            <h2>Data Quality</h2>
            <h3>Missing Values</h3>
            <table>
                <tr>
                    <th>Column</th>
                    <th>Missing Count</th>
                    <th>Missing %</th>
                    <th>Status</th>
                </tr>
"""
    
    # Add missing value rows
    for col in profile['missing'].keys():
        missing_count = profile['missing'][col]
        missing_pct = profile['missing_pct'][col]
        status = '✓ Clean' if missing_count == 0 else f'⚠ {missing_pct:.1f}% missing'
        
        html += f"""
                <tr>
                    <td>{col}</td>
                    <td>{missing_count:,}</td>
                    <td>{missing_pct:.2f}%</td>
                    <td>{status}</td>
                </tr>
"""
    
    html += """
            </table>
        </section>
        
        <!-- Statistical Summary -->
        <section class="card">
            <h2>Statistical Summary</h2>
"""
    
    # Add numeric statistics if available
    if 'numeric' in stats and stats['numeric']:
        html += """
            <h3>Numeric Features</h3>
            <table>
                <tr>
                    <th>Column</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Mean</th>
                    <th>Median</th>
                    <th>Std Dev</th>
                </tr>
"""
        for col, values in stats['numeric'].items():
            if col in ['count', '25%', '75%']:
                continue
            html += f"""
                <tr>
                    <td>{col}</td>
                    <td>{values.get('min', 'N/A'):.2f if isinstance(values.get('min'), (int, float)) else 'N/A'}</td>
                    <td>{values.get('max', 'N/A'):.2f if isinstance(values.get('max'), (int, float)) else 'N/A'}</td>
                    <td>{values.get('mean', 'N/A'):.2f if isinstance(values.get('mean'), (int, float)) else 'N/A'}</td>
                    <td>{values.get('50%', 'N/A'):.2f if isinstance(values.get('50%'), (int, float)) else 'N/A'}</td>
                    <td>{values.get('std', 'N/A'):.2f if isinstance(values.get('std'), (int, float)) else 'N/A'}</td>
                </tr>
"""
        html += "            </table>\n"
    
    # Add categorical statistics if available
    if 'categorical' in stats and stats['categorical']:
        html += """
            <h3>Categorical Features</h3>
            <table>
                <tr>
                    <th>Column</th>
                    <th>Unique Values</th>
                    <th>Most Frequent</th>
                    <th>Frequency</th>
                </tr>
"""
        for col, values in stats['categorical'].items():
            html += f"""
                <tr>
                    <td>{col}</td>
                    <td>{values['unique']}</td>
                    <td>{values['top']}</td>
                    <td>{values['freq']:,}</td>
                </tr>
"""
        html += "            </table>\n"
    
    html += """
        </section>
        
        <!-- Visualizations -->
        <section class="card">
            <h2>Visualizations</h2>
            
            <h3>Correlation Matrix</h3>
            <div class="image-container">
                <img src="correlation_matrix.png" alt="Correlation Matrix">
            </div>
            
            <h3>Feature Distributions</h3>
            <div class="image-container">
                <img src="distributions.png" alt="Distributions">
            </div>
        </section>
        
        <!-- Recommendations -->
        <section class="card">
            <h2>Recommendations</h2>
            <ul>
"""
    
    # Add recommendations based on analysis
    if profile['duplicates'] > 0:
        html += f"                <li>Remove {profile['duplicates']} duplicate rows</li>\n"
    
    high_missing = [col for col, pct in profile['missing_pct'].items() if pct > 20]
    if high_missing:
        html += f"                <li>Consider handling missing values in: {', '.join(high_missing)}</li>\n"
    
    if 'skewness' in stats:
        skewed = [col for col, skew in stats['skewness'].items() if abs(skew) > 1]
        if skewed:
            html += f"                <li>Apply log transformation to skewed features: {', '.join(skewed)}</li>\n"
    
    html += """
            </ul>
        </section>
    </div>
    
    <footer>
        <p>Generated by Data Analysis Skill</p>
    </footer>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Saved HTML report: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_analysis.py <data_file>")
        print("Supported formats: CSV, Excel, JSON")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("AUTOMATED DATA ANALYSIS")
    print("="*60 + "\n")
    
    # Load data
    print("Step 1: Loading data...")
    df = load_data(filepath)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(filepath), 'analysis_output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate profile
    print("\nStep 2: Generating data profile...")
    profile = generate_data_profile(df)
    
    # Generate statistics
    print("Step 3: Calculating statistics...")
    stats = generate_statistics(df)
    
    # Create visualizations
    print("\nStep 4: Creating visualizations...")
    create_correlation_matrix(df, os.path.join(output_dir, 'correlation_matrix.png'))
    create_distribution_plots(df, os.path.join(output_dir, 'distributions.png'))
    create_categorical_plots(df, output_dir)
    
    # Generate report
    print("\nStep 5: Generating HTML report...")
    generate_html_report(df, profile, stats, os.path.join(output_dir, 'analysis_report.html'))
    
    print("\n" + "="*60)
    print("✓ Analysis Complete!")
    print(f"Output directory: {output_dir}")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
