---
name: data-analysis
description: Comprehensive data analysis workflow supporting data cleaning, exploration, visualization, statistical analysis, and report generation. Works with CSV, Excel, JSON, and SQL databases. Use when user needs to analyze datasets, perform statistical tests, create visualizations, or generate data insights.
---

# Data Analysis Skill

A complete toolkit for professional data analysis, from raw data to actionable insights.

## Quick Start

### 1. Load Data

```python
import pandas as pd

# CSV
df = pd.read_csv('data.csv')

# Excel
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# JSON
df = pd.read_json('data.json')

# SQL
import sqlite3
conn = sqlite3.connect('database.db')
df = pd.read_sql('SELECT * FROM table', conn)
```

### 2. Quick Overview

```python
# Basic info
df.info()
df.describe()
df.head()

# Check missing values
df.isnull().sum()

# Check duplicates
df.duplicated().sum()
```

### 3. Generate Report

Run `scripts/auto_analysis.py` for automated comprehensive analysis.

---

## Analysis Workflow

### Phase 1: Data Profiling

Understand the dataset structure and quality:

1. **Dimensions**: `df.shape`
2. **Data types**: `df.dtypes`
3. **Missing values**: `df.isnull().sum()`
4. **Unique values**: `df.nunique()`
5. **Statistics**: `df.describe()`

**Automated profiling**: Run `scripts/profile_data.py` for a complete data quality report.

### Phase 2: Data Cleaning

Common cleaning operations:

```python
# Handle missing values
df.fillna(df.mean(), inplace=True)  # Numeric: mean
df.fillna(df.mode()[0], inplace=True)  # Categorical: mode
df.dropna(subset=['important_col'], inplace=True)  # Drop if critical

# Remove duplicates
df.drop_duplicates(inplace=True)

# Fix data types
df['date'] = pd.to_datetime(df['date'])
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

# Standardize text
df['category'] = df['category'].str.lower().str.strip()

# Handle outliers
from scipy import stats
df = df[(np.abs(stats.zscore(df.select_dtypes(include=[np.number]))) < 3).all(axis=1)]
```

**Advanced cleaning**: See [references/cleaning.md](references/cleaning.md) for detailed patterns.

### Phase 3: Exploratory Data Analysis (EDA)

#### Univariate Analysis

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Numeric: histogram
df['column'].hist(bins=30)
plt.show()

# Categorical: bar chart
df['category'].value_counts().plot(kind='bar')
plt.show()
```

#### Bivariate Analysis

```python
# Numeric vs Numeric: scatter plot
df.plot.scatter(x='var1', y='var2')
plt.show()

# Correlation heatmap
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
plt.show()

# Categorical vs Numeric: box plot
df.boxplot(column='numeric_col', by='category')
plt.show()
```

#### Multivariate Analysis

```python
# Pair plot
sns.pairplot(df)
plt.show()

# Grouped analysis
df.groupby('category').agg({
    'numeric1': 'mean',
    'numeric2': 'sum'
})
```

**Visualization patterns**: See [references/visualizations.md](references/visualizations.md) for 20+ chart templates.

### Phase 4: Statistical Analysis

#### Hypothesis Testing

```python
from scipy import stats

# T-test: compare two groups
group1 = df[df['category'] == 'A']['value']
group2 = df[df['category'] == 'B']['value']
t_stat, p_value = stats.ttest_ind(group1, group2)

# Chi-square test: categorical association
contingency_table = pd.crosstab(df['cat1'], df['cat2'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

# ANOVA: compare multiple groups
groups = [df[df['category'] == cat]['value'] for cat in df['category'].unique()]
f_stat, p_value = stats.f_oneway(*groups)
```

#### Correlation Analysis

```python
# Pearson correlation (linear)
corr = df['var1'].corr(df['var2'])

# Spearman correlation (non-linear)
corr = df['var1'].corr(df['var2'], method='spearman')
```

**Statistical tests guide**: See [references/statistics.md](references/statistics.md).

### Phase 5: Advanced Analysis

#### Time Series

```python
# Set datetime index
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# Resample
monthly = df.resample('M').sum()
daily_mean = df.resample('D').mean()

# Rolling statistics
df['rolling_mean'] = df['value'].rolling(window=7).mean()
df['rolling_std'] = df['value'].rolling(window=7).std()

# Decomposition
from statsmodels.tsa.seasonal import seasonal_decompose
decomposition = seasonal_decompose(df['value'], model='additive', period=12)
decomposition.plot()
plt.show()
```

#### Machine Learning

```python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# Prepare features
X = df[['feature1', 'feature2', 'feature3']]
y = df['target']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
```

**ML patterns**: See [references/machine_learning.md](references/machine_learning.md).

---

## Automated Tools

### Full Analysis Pipeline

Run complete automated analysis:

```bash
python scripts/auto_analysis.py data.csv
```

Outputs:
- `data_profile.html` - Interactive data profile
- `correlation_matrix.png` - Correlation heatmap
- `distributions.png` - Feature distributions
- `analysis_report.html` - Comprehensive HTML report

### Quick Profiler

Generate data quality report:

```bash
python scripts/profile_data.py data.csv
```

Outputs:
- Missing value analysis
- Data type recommendations
- Outlier detection
- Unique value counts
- Statistical summary

---

## Output Best Practices

### Code Organization

```python
# Structure analysis notebooks/scripts as:
# 1. Imports and setup
# 2. Data loading
# 3. Data profiling
# 4. Data cleaning
# 5. EDA
# 6. Statistical analysis
# 7. Advanced analysis (if needed)
# 8. Conclusions and recommendations
```

### Visualization Standards

- Use consistent color palette: `sns.set_palette("husl")`
- Add titles and labels to all charts
- Use appropriate chart types:
  - **Trends** → Line charts
  - **Comparisons** → Bar charts
  - **Distributions** → Histograms/Box plots
  - **Relationships** → Scatter plots
  - **Proportions** → Pie charts (max 5 categories)

### Report Template

Structure findings as:

```markdown
# Data Analysis Report

## Executive Summary
- Key findings (3-5 bullet points)

## Dataset Overview
- Shape, features, data types
- Quality issues identified

## Key Insights
### Insight 1: [Title]
- Observation
- Evidence (chart/statistic)
- Business implication

### Insight 2: [Title]
...

## Recommendations
1. [Actionable recommendation based on data]
2. ...

## Appendix
- Detailed statistics
- All visualizations
```

---

## Common Scenarios

### Scenario 1: Sales Data Analysis

```python
# Load
df = pd.read_csv('sales.csv')
df['date'] = pd.to_datetime(df['date'])

# Analyze by time
daily_sales = df.groupby('date')['revenue'].sum()
monthly_sales = df.resample('M', on='date')['revenue'].sum()

# Top products
top_products = df.groupby('product')['revenue'].sum().sort_values(ascending=False).head(10)

# Growth rate
df['growth_rate'] = df.groupby('product')['revenue'].pct_change()
```

### Scenario 2: Customer Segmentation

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Prepare features
features = df[['age', 'income', 'spending_score']]
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

# Clustering
kmeans = KMeans(n_clusters=4, random_state=42)
df['segment'] = kmeans.fit_predict(features_scaled)

# Analyze segments
segment_profile = df.groupby('segment').agg({
    'age': 'mean',
    'income': 'mean',
    'spending_score': 'mean',
    'customer_id': 'count'
})
```

### Scenario 3: A/B Test Analysis

```python
from scipy import stats

# Group data
control = df[df['group'] == 'control']['conversion']
treatment = df[df['group'] == 'treatment']['conversion']

# Statistical test
t_stat, p_value = stats.ttest_ind(control, treatment)

# Effect size
effect_size = (treatment.mean() - control.mean()) / control.mean()

# Confidence interval
from scipy.stats import t
mean_diff = treatment.mean() - control.mean()
se = np.sqrt(treatment.var()/len(treatment) + control.var()/len(control))
ci = t.interval(0.95, len(treatment)+len(control)-2, loc=mean_diff, scale=se)
```

---

## Reference Files

- **[cleaning.md](references/cleaning.md)**: Advanced data cleaning patterns and edge cases
- **[visualizations.md](references/visualizations.md)**: 20+ visualization templates and best practices
- **[statistics.md](references/statistics.md)**: Statistical tests guide and when to use each
- **[machine_learning.md](references/machine_learning.md)**: ML workflows for data analysis

---

## Quick Reference

| Task | Code |
|------|------|
| Load CSV | `pd.read_csv('file.csv')` |
| Basic stats | `df.describe()` |
| Missing values | `df.isnull().sum()` |
| Drop duplicates | `df.drop_duplicates()` |
| Group by | `df.groupby('col').agg({'num': 'mean'})` |
| Pivot table | `df.pivot_table(values='num', index='row', columns='col')` |
| Correlation | `df.corr()` |
| Save to CSV | `df.to_csv('output.csv', index=False)` |
