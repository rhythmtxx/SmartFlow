# Data Visualization Patterns

## Table of Contents
1. [Setup and Styling](#setup-and-styling)
2. [Distribution Plots](#distribution-plots)
3. [Comparison Plots](#comparison-plots)
4. [Relationship Plots](#relationship-plots)
5. [Time Series Plots](#time-series-plots)
6. [Categorical Plots](#categorical-plots)
7. [Advanced Visualizations](#advanced-visualizations)

---

## Setup and Styling

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set style
plt.style.use('seaborn-darkgrid')
sns.set_palette("husl")
sns.set_context("notebook")  # paper, notebook, talk, poster

# Figure size defaults
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 12

# Color palettes
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
```

---

## Distribution Plots

### Histogram with KDE

```python
# Single distribution
fig, ax = plt.subplots(figsize=(10, 6))
sns.histplot(data=df, x='value', bins=30, kde=True, color='#4ECDC4')
plt.title('Distribution of Values', fontsize=16, fontweight='bold')
plt.xlabel('Value', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.tight_layout()
plt.savefig('distribution.png', dpi=300, bbox_inches='tight')
plt.show()

# Multiple distributions
fig, ax = plt.subplots(figsize=(10, 6))
for col in ['value1', 'value2', 'value3']:
    sns.kdeplot(data=df, x=col, label=col, fill=True, alpha=0.5)
plt.legend()
plt.title('Comparing Distributions')
plt.show()
```

### Box Plot

```python
# Single box plot
fig, ax = plt.subplots(figsize=(8, 6))
sns.boxplot(data=df, y='value', color='#4ECDC4')
plt.title('Value Distribution')
plt.show()

# Grouped box plot
fig, ax = plt.subplots(figsize=(12, 6))
sns.boxplot(data=df, x='category', y='value', palette='husl')
plt.title('Value Distribution by Category')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### Violin Plot

```python
fig, ax = plt.subplots(figsize=(12, 6))
sns.violinplot(data=df, x='category', y='value', palette='husl')
plt.title('Value Distribution by Category (Violin)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

---

## Comparison Plots

### Bar Chart

```python
# Simple bar chart
category_counts = df['category'].value_counts()
fig, ax = plt.subplots(figsize=(10, 6))
category_counts.plot(kind='bar', color='#4ECDC4', ax=ax)
plt.title('Count by Category')
plt.xlabel('Category')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Grouped bar chart
pivot_data = df.groupby(['category', 'group'])['value'].mean().unstack()
pivot_data.plot(kind='bar', figsize=(12, 6), colormap='viridis')
plt.title('Average Value by Category and Group')
plt.xlabel('Category')
plt.ylabel('Average Value')
plt.xticks(rotation=45)
plt.legend(title='Group')
plt.tight_layout()
plt.show()

# Horizontal bar chart (good for many categories)
category_counts.sort_values().plot(kind='barh', figsize=(10, 8), color='#4ECDC4')
plt.title('Count by Category')
plt.xlabel('Count')
plt.tight_layout()
plt.show()
```

### Stacked Bar Chart

```python
pivot_data = df.groupby(['category', 'group']).size().unstack(fill_value=0)
pivot_data.plot(kind='bar', stacked=True, figsize=(12, 6), colormap='viridis')
plt.title('Distribution by Category and Group')
plt.xlabel('Category')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.legend(title='Group', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()
```

---

## Relationship Plots

### Scatter Plot

```python
# Basic scatter
fig, ax = plt.subplots(figsize=(10, 8))
sns.scatterplot(data=df, x='var1', y='var2', alpha=0.6, color='#4ECDC4')
plt.title('Relationship between Var1 and Var2')
plt.xlabel('Variable 1')
plt.ylabel('Variable 2')
plt.tight_layout()
plt.show()

# Scatter with categories
fig, ax = plt.subplots(figsize=(10, 8))
sns.scatterplot(data=df, x='var1', y='var2', hue='category', style='category', s=100)
plt.title('Var1 vs Var2 by Category')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

# Scatter with regression line
fig, ax = plt.subplots(figsize=(10, 8))
sns.regplot(data=df, x='var1', y='var2', scatter_kws={'alpha':0.5}, line_kws={'color': 'red'})
plt.title('Var1 vs Var2 with Regression Line')
plt.tight_layout()
plt.show()
```

### Correlation Heatmap

```python
# Calculate correlation matrix
numeric_cols = df.select_dtypes(include=[np.number]).columns
corr_matrix = df[numeric_cols].corr()

# Plot heatmap
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
            center=0, square=True, linewidths=1, ax=ax)
plt.title('Correlation Matrix', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('correlation_matrix.png', dpi=300, bbox_inches='tight')
plt.show()
```

### Pair Plot

```python
# All numeric variables
sns.pairplot(df[numeric_cols], diag_kind='kde', plot_kws={'alpha': 0.6})
plt.suptitle('Pairwise Relationships', y=1.01)
plt.show()

# With categorical coloring
sns.pairplot(df[['var1', 'var2', 'var3', 'category']], hue='category', diag_kind='kde')
plt.suptitle('Pairwise Relationships by Category', y=1.01)
plt.show()
```

---

## Time Series Plots

### Line Plot

```python
# Single time series
df['date'] = pd.to_datetime(df['date'])
df_sorted = df.sort_values('date')

fig, ax = plt.subplots(figsize=(14, 6))
plt.plot(df_sorted['date'], df_sorted['value'], linewidth=2, color='#4ECDC4')
plt.title('Value Over Time')
plt.xlabel('Date')
plt.ylabel('Value')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Multiple time series
fig, ax = plt.subplots(figsize=(14, 6))
for col in ['value1', 'value2', 'value3']:
    plt.plot(df_sorted['date'], df_sorted[col], label=col, linewidth=2)
plt.title('Multiple Metrics Over Time')
plt.xlabel('Date')
plt.ylabel('Value')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### Time Series with Rolling Statistics

```python
df['rolling_mean'] = df['value'].rolling(window=7).mean()
df['rolling_std'] = df['value'].rolling(window=7).std()

fig, ax = plt.subplots(figsize=(14, 8))
plt.plot(df['date'], df['value'], alpha=0.3, label='Original', color='#4ECDC4')
plt.plot(df['date'], df['rolling_mean'], label='7-Day Rolling Mean', color='#FF6B6B', linewidth=2)
plt.fill_between(df['date'], 
                 df['rolling_mean'] - df['rolling_std'],
                 df['rolling_mean'] + df['rolling_std'],
                 alpha=0.2, color='#FF6B6B', label='±1 Std Dev')
plt.title('Time Series with Rolling Statistics')
plt.xlabel('Date')
plt.ylabel('Value')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### Seasonal Decomposition

```python
from statsmodels.tsa.seasonal import seasonal_decompose

df_ts = df.set_index('date')['value']
decomposition = seasonal_decompose(df_ts, model='additive', period=12)

fig, axes = plt.subplots(4, 1, figsize=(14, 12))
decomposition.observed.plot(ax=axes[0], title='Observed')
decomposition.trend.plot(ax=axes[1], title='Trend')
decomposition.seasonal.plot(ax=axes[2], title='Seasonal')
decomposition.resid.plot(ax=axes[3], title='Residual')
plt.tight_layout()
plt.show()
```

---

## Categorical Plots

### Count Plot

```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.countplot(data=df, x='category', order=df['category'].value_counts().index, palette='husl')
plt.title('Count by Category')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Horizontal count plot
fig, ax = plt.subplots(figsize=(8, 10))
sns.countplot(data=df, y='category', order=df['category'].value_counts().index, palette='husl')
plt.title('Count by Category')
plt.tight_layout()
plt.show()
```

### Pie Chart

```python
# Simple pie chart (max 5-6 categories)
category_counts = df['category'].value_counts().head(5)
fig, ax = plt.subplots(figsize=(10, 8))
plt.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', 
        colors=sns.color_palette('husl', len(category_counts)), startangle=90)
plt.title('Distribution by Category')
plt.tight_layout()
plt.show()

# Pie chart with other category
top_5 = df['category'].value_counts().head(5)
top_5['Other'] = df['category'].value_counts()[5:].sum()

fig, ax = plt.subplots(figsize=(10, 8))
plt.pie(top_5, labels=top_5.index, autopct='%1.1f%%', 
        colors=sns.color_palette('husl', len(top_5)), startangle=90)
plt.title('Distribution by Category')
plt.tight_layout()
plt.show()
```

---

## Advanced Visualizations

### Heatmap of Categories Over Time

```python
# Pivot data for heatmap
heatmap_data = df.pivot_table(values='value', index='category', columns='month', aggfunc='sum')

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(heatmap_data, annot=True, fmt='.0f', cmap='YlOrRd', linewidths=0.5)
plt.title('Value by Category and Month')
plt.xlabel('Month')
plt.ylabel('Category')
plt.tight_layout()
plt.show()
```

### Facet Grid

```python
g = sns.FacetGrid(df, col='category1', row='category2', height=4, aspect=1.2)
g.map_dataframe(sns.scatterplot, x='var1', y='var2', alpha=0.6)
g.add_legend()
g.fig.suptitle('Relationship by Categories', y=1.01)
plt.tight_layout()
plt.show()
```

### 3D Scatter Plot

```python
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
scatter = ax.scatter(df['var1'], df['var2'], df['var3'], 
                     c=df['category'].astype('category').cat.codes, 
                     cmap='viridis', alpha=0.6, s=50)
ax.set_xlabel('Variable 1')
ax.set_ylabel('Variable 2')
ax.set_zlabel('Variable 3')
plt.title('3D Scatter Plot')
plt.colorbar(scatter, label='Category')
plt.tight_layout()
plt.show()
```

### Bubble Chart

```python
fig, ax = plt.subplots(figsize=(12, 8))
scatter = plt.scatter(df['var1'], df['var2'], s=df['var3']*10, 
                      c=df['category'].astype('category').cat.codes,
                      alpha=0.6, cmap='viridis')
plt.xlabel('Variable 1')
plt.ylabel('Variable 2')
plt.title('Bubble Chart')
plt.colorbar(scatter, label='Category')
plt.tight_layout()
plt.show()
```

---

## Best Practices

1. **Always add titles and labels** - Make charts self-explanatory
2. **Use appropriate scales** - Linear vs logarithmic
3. **Limit categories** - Max 5-7 for pie charts, 10-12 for bar charts
4. **Color wisely** - Use colorblind-friendly palettes
5. **Annotate key points** - Highlight important insights
6. **Export properly** - Use `dpi=300` for presentations, `bbox_inches='tight'` to avoid clipping
7. **Consistent styling** - Same fonts, colors, and formatting across all charts in a report
