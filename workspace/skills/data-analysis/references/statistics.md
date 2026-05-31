# Statistical Analysis Guide

## Table of Contents
1. [Descriptive Statistics](#descriptive-statistics)
2. [Hypothesis Testing](#hypothesis-testing)
3. [Correlation Analysis](#correlation-analysis)
4. [Regression Analysis](#regression-analysis)
5. [Non-Parametric Tests](#non-parametric-tests)

---

## Descriptive Statistics

### Central Tendency

```python
import pandas as pd
import numpy as np

# Mean (sensitive to outliers)
mean = df['column'].mean()

# Median (robust to outliers)
median = df['column'].median()

# Mode (most frequent)
mode = df['column'].mode()[0]

# Trimmed mean (remove extreme values)
from scipy.stats import trim_mean
trimmed_mean = trim_mean(df['column'], proportiontocut=0.1)  # Remove top/bottom 10%
```

### Dispersion

```python
# Variance
variance = df['column'].var()

# Standard deviation
std = df['column'].std()

# Coefficient of variation (relative variability)
cv = (df['column'].std() / df['column'].mean()) * 100

# Range
range_val = df['column'].max() - df['column'].min()

# Interquartile range (robust)
iqr = df['column'].quantile(0.75) - df['column'].quantile(0.25)

# Percentiles
percentiles = df['column'].quantile([0.25, 0.5, 0.75, 0.95, 0.99])
```

### Shape

```python
from scipy import stats

# Skewness (asymmetry)
skewness = df['column'].skew()
# Interpretation: 
# -0.5 to 0.5: fairly symmetrical
# -1 to -0.5 or 0.5 to 1: moderately skewed
# < -1 or > 1: highly skewed

# Kurtosis (tailedness)
kurtosis = df['column'].kurtosis()
# Interpretation:
# ≈ 0: normal distribution (mesokurtic)
# > 0: heavy tails (leptokurtic)
# < 0: light tails (platykurtic)

# Normality test
stat, p_value = stats.normaltest(df['column'])
# p < 0.05: reject normality
```

---

## Hypothesis Testing

### Test Selection Guide

| Data Type | Groups | Test | Use When |
|-----------|--------|------|----------|
| Continuous | 1 | One-sample t-test | Compare mean to known value |
| Continuous | 2 independent | Independent t-test | Compare two groups |
| Continuous | 2 paired | Paired t-test | Before-after comparison |
| Continuous | 3+ independent | ANOVA | Compare multiple groups |
| Continuous | 3+ related | Repeated measures ANOVA | Multiple measurements same subjects |
| Categorical | 2+ | Chi-square | Test association |
| Ordinal | 2 independent | Mann-Whitney U | Non-parametric alternative to t-test |
| Ordinal | 3+ independent | Kruskal-Wallis | Non-parametric alternative to ANOVA |

### One-Sample t-test

```python
from scipy import stats

# Test if mean differs from a known value
t_stat, p_value = stats.ttest_1samp(df['value'], popmean=50)

# Effect size (Cohen's d)
cohens_d = (df['value'].mean() - 50) / df['value'].std()

# Interpretation
alpha = 0.05
if p_value < alpha:
    print(f"Reject H0: Mean significantly differs from 50 (p={p_value:.4f})")
else:
    print(f"Fail to reject H0: No significant difference (p={p_value:.4f})")
```

### Independent Samples t-test

```python
# Compare two independent groups
group1 = df[df['group'] == 'A']['value']
group2 = df[df['group'] == 'B']['value']

# Check equal variance assumption (Levene's test)
lev_stat, lev_p = stats.levene(group1, group2)
equal_var = lev_p > 0.05  # True if variances are equal

# t-test
t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=equal_var)

# Effect size (Cohen's d)
pooled_std = np.sqrt(((len(group1)-1)*group1.var() + (len(group2)-1)*group2.var()) / (len(group1)+len(group2)-2))
cohens_d = (group1.mean() - group2.mean()) / pooled_std
# Interpretation: 0.2=small, 0.5=medium, 0.8=large

# Confidence interval
mean_diff = group1.mean() - group2.mean()
se = np.sqrt(group1.var()/len(group1) + group2.var()/len(group2))
ci = stats.t.interval(0.95, df=len(group1)+len(group2)-2, loc=mean_diff, scale=se)
```

### Paired Samples t-test

```python
# Before-after comparison
before = df['before']
after = df['after']

t_stat, p_value = stats.ttest_rel(before, after)

# Effect size
cohens_d = (after.mean() - before.mean()) / (after - before).std()
```

### ANOVA (Analysis of Variance)

```python
# One-way ANOVA
groups = [df[df['category'] == cat]['value'] for cat in df['category'].unique()]
f_stat, p_value = stats.f_oneway(*groups)

# If significant, post-hoc test (Tukey HSD)
from statsmodels.stats.multicomp import pairwise_tukeyhsd

tukey = pairwise_tukeyhsd(df['value'], df['category'], alpha=0.05)
print(tukey)

# Effect size (eta-squared)
ss_between = sum(len(g) * (g.mean() - df['value'].mean())**2 for g in groups)
ss_total = sum((df['value'] - df['value'].mean())**2)
eta_squared = ss_between / ss_total
# Interpretation: 0.01=small, 0.06=medium, 0.14=large
```

### Chi-Square Test

```python
# Test association between two categorical variables
contingency_table = pd.crosstab(df['var1'], df['var2'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

# Effect size (Cramér's V)
n = contingency_table.sum().sum()
min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
cramers_v = np.sqrt(chi2 / (n * min_dim))
# Interpretation: 0.1=small, 0.3=medium, 0.5=large

# Goodness of fit (one categorical variable vs expected proportions)
observed = df['category'].value_counts()
expected = [len(df) / len(observed)] * len(observed)  # Equal proportions
chi2, p_value = stats.chisquare(observed, expected)
```

---

## Correlation Analysis

### Pearson Correlation

```python
# Linear relationship between two continuous variables
corr, p_value = stats.pearsonr(df['var1'], df['var2'])

# Interpretation:
# 0.0-0.3: weak
# 0.3-0.7: moderate
# 0.7-1.0: strong

# Correlation matrix
corr_matrix = df[['var1', 'var2', 'var3']].corr(method='pearson')

# Test if correlation is significantly different from 0
n = len(df)
t_stat = corr * np.sqrt(n-2) / np.sqrt(1 - corr**2)
p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-2))
```

### Spearman Correlation

```python
# Monotonic relationship (non-parametric)
corr, p_value = stats.spearmanr(df['var1'], df['var2'])

# Use when:
# - Relationship is monotonic but not linear
# - Data has outliers
# - Data is ordinal
```

### Kendall's Tau

```python
# For ordinal data or small sample sizes
corr, p_value = stats.kendalltau(df['var1'], df['var2'])
```

---

## Regression Analysis

### Simple Linear Regression

```python
from scipy import stats
import statsmodels.api as sm

# Method 1: scipy
slope, intercept, r_value, p_value, std_err = stats.linregress(df['x'], df['y'])

# Method 2: statsmodels (more detailed output)
X = sm.add_constant(df['x'])  # Add intercept
model = sm.OLS(df['y'], X).fit()
print(model.summary())

# Predictions
predictions = model.predict(X)
residuals = df['y'] - predictions

# Check assumptions
# 1. Linearity: plot y vs x
# 2. Normality of residuals
stats.normaltest(residuals)
# 3. Homoscedasticity: plot residuals vs predicted
plt.scatter(predictions, residuals)
plt.axhline(y=0, color='r', linestyle='--')
```

### Multiple Linear Regression

```python
import statsmodels.api as sm

# Prepare features
X = df[['var1', 'var2', 'var3']]
X = sm.add_constant(X)
y = df['target']

# Fit model
model = sm.OLS(y, X).fit()
print(model.summary())

# Key metrics:
# - R-squared: proportion of variance explained
# - Adj. R-squared: adjusted for number of predictors
# - F-statistic: overall model significance
# - Coefficients: impact of each variable
# - P-values: significance of each coefficient

# Predict
df['predicted'] = model.predict(X)

# Diagnostics
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Check multicollinearity (VIF)
vif_data = pd.DataFrame()
vif_data["Variable"] = X.columns
vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
# VIF > 10 indicates multicollinearity
```

---

## Non-Parametric Tests

### Mann-Whitney U Test (alternative to independent t-test)

```python
# Compare two independent groups (no normality assumption)
group1 = df[df['group'] == 'A']['value']
group2 = df[df['group'] == 'B']['value']

u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')

# Effect size (rank-biserial correlation)
n1, n2 = len(group1), len(group2)
r = 1 - (2 * u_stat) / (n1 * n2)  # Common language effect size
```

### Wilcoxon Signed-Rank Test (alternative to paired t-test)

```python
# Before-after comparison (paired samples, no normality assumption)
stat, p_value = stats.wilcoxon(df['before'], df['after'])
```

### Kruskal-Wallis Test (alternative to ANOVA)

```python
# Compare 3+ independent groups (no normality assumption)
groups = [df[df['category'] == cat]['value'] for cat in df['category'].unique()]
h_stat, p_value = stats.kruskal(*groups)

# Post-hoc: Dunn's test
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

p_values = []
comparisons = []
categories = df['category'].unique()

for i in range(len(categories)):
    for j in range(i+1, len(categories)):
        g1 = df[df['category'] == categories[i]]['value']
        g2 = df[df['category'] == categories[j]]['value']
        _, p = mannwhitneyu(g1, g2)
        p_values.append(p)
        comparisons.append(f"{categories[i]} vs {categories[j]}")

# Bonferroni correction
_, adjusted_p, _, _ = multipletests(p_values, method='bonferroni')
```

### Friedman Test (alternative to repeated measures ANOVA)

```python
# Compare 3+ related groups
stat, p_value = stats.friedmanchisquare(df['time1'], df['time2'], df['time3'])
```

---

## Power Analysis

```python
from statsmodels.stats.power import TTestIndPower, TTestPower

# Calculate required sample size
effect_size = 0.5  # Cohen's d (0.2=small, 0.5=medium, 0.8=large)
alpha = 0.05
power = 0.8

power_analysis = TTestIndPower()
sample_size = power_analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power)
print(f"Required sample size per group: {int(np.ceil(sample_size))}")

# Calculate power for given sample size
power = power_analysis.solve_power(effect_size=effect_size, alpha=alpha, nobs1=50)
print(f"Power: {power:.2f}")

# Calculate minimum detectable effect size
effect = power_analysis.solve_power(alpha=alpha, power=power, nobs1=50)
print(f"Minimum detectable effect size: {effect:.2f}")
```

---

## Multiple Testing Correction

```python
from statsmodels.stats.multitest import multipletests

# Example: testing multiple correlations
p_values = [0.001, 0.02, 0.03, 0.04, 0.05, 0.06, 0.10]

# Bonferroni correction (most conservative)
reject_bonf, p_bonf, _, _ = multipletests(p_values, alpha=0.05, method='bonferroni')

# Benjamini-Hochberg (FDR - less conservative)
reject_fdr, p_fdr, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')

# Compare
pd.DataFrame({
    'original': p_values,
    'bonferroni': p_bonf,
    'FDR': p_fdr,
    'reject_bonf': reject_bonf,
    'reject_fdr': reject_fdr
})
```

---

## Effect Size Interpretation Guide

| Test | Effect Size | Small | Medium | Large |
|------|-------------|-------|--------|-------|
| t-test | Cohen's d | 0.2 | 0.5 | 0.8 |
| ANOVA | Eta-squared (η²) | 0.01 | 0.06 | 0.14 |
| Correlation | r | 0.1 | 0.3 | 0.5 |
| Chi-square | Cramér's V | 0.1 | 0.3 | 0.5 |
| Regression | R² | 0.02 | 0.13 | 0.26 |

---

## Assumptions Checklist

### Parametric Tests (t-test, ANOVA)
- [ ] Normality: Shapiro-Wilk test or Q-Q plot
- [ ] Homogeneity of variance: Levene's test
- [ ] Independence of observations
- [ ] No significant outliers

### Regression
- [ ] Linearity: Scatter plot of y vs x
- [ ] Normality of residuals: Q-Q plot
- [ ] Homoscedasticity: Residuals vs predicted plot
- [ ] No multicollinearity: VIF < 10
- [ ] Independence: Durbin-Watson test
