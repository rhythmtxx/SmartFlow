# Advanced Data Cleaning Patterns

## Table of Contents
1. [Missing Value Strategies](#missing-value-strategies)
2. [Outlier Detection & Treatment](#outlier-detection--treatment)
3. [Data Type Conversions](#data-type-conversions)
4. [Text Cleaning](#text-cleaning)
5. [Date/Time Handling](#datetime-handling)
6. [Duplicate Management](#duplicate-management)

---

## Missing Value Strategies

### Strategy Selection Guide

| Strategy | When to Use | Pros | Cons |
|----------|-------------|------|------|
| **Delete** | < 5% missing, MCAR | Simple, no bias | Loss of data |
| **Mean/Median** | Numeric, normal distribution | Preserves N | Reduces variance |
| **Mode** | Categorical | Preserves N | May overrepresent |
| **Forward/Backward Fill** | Time series | Maintains trend | Not for large gaps |
| **Interpolation** | Time series, numeric | Smooth | Assumes continuity |
| **Predictive** | Complex patterns | Most accurate | Requires ML model |

### Implementation Examples

```python
import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer

# 1. Simple imputation
df['column'].fillna(df['column'].mean(), inplace=True)  # Mean
df['column'].fillna(df['column'].median(), inplace=True)  # Median (better for skewed)
df['column'].fillna(df['column'].mode()[0], inplace=True)  # Mode (categorical)

# 2. Forward/Backward fill (time series)
df['value'].fillna(method='ffill', inplace=True)  # Forward fill
df['value'].fillna(method='bfill', inplace=True)  # Backward fill

# 3. Interpolation
df['value'].interpolate(method='linear', inplace=True)  # Linear
df['value'].interpolate(method='polynomial', order=2, inplace=True)  # Polynomial

# 4. KNN Imputation (advanced)
imputer = KNNImputer(n_neighbors=5)
df_numeric = df.select_dtypes(include=[np.number])
df[df_numeric.columns] = imputer.fit_transform(df_numeric)

# 5. Conditional imputation
df.loc[(df['age'].isna()) & (df['group'] == 'A'), 'age'] = df[df['group'] == 'A']['age'].mean()
df.loc[(df['age'].isna()) & (df['group'] == 'B'), 'age'] = df[df['group'] == 'B']['age'].mean()

# 6. Flag missing values before imputation
df['column_missing'] = df['column'].isna().astype(int)
df['column'].fillna(df['column'].mean(), inplace=True)
```

---

## Outlier Detection & Treatment

### Detection Methods

```python
import pandas as pd
import numpy as np
from scipy import stats

# Method 1: Z-Score (normal distribution)
z_scores = np.abs(stats.zscore(df['column']))
outliers_z = df[z_scores > 3]

# Method 2: IQR (Interquartile Range) - robust for any distribution
Q1 = df['column'].quantile(0.25)
Q3 = df['column'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
outliers_iqr = df[(df['column'] < lower_bound) | (df['column'] > upper_bound)]

# Method 3: Percentile method
lower_pct = df['column'].quantile(0.01)
upper_pct = df['column'].quantile(0.99)
outliers_pct = df[(df['column'] < lower_pct) | (df['column'] > upper_pct)]

# Method 4: Isolation Forest (multivariate)
from sklearn.ensemble import IsolationForest
iso = IsolationForest(contamination=0.1, random_state=42)
outliers_mask = iso.fit_predict(df.select_dtypes(include=[np.number])) == -1
outliers_iso = df[outliers_mask]
```

### Treatment Options

```python
# Option 1: Remove outliers
df_clean = df[(df['column'] >= lower_bound) & (df['column'] <= upper_bound)]

# Option 2: Cap outliers (winsorization)
df['column_capped'] = df['column'].clip(lower=lower_bound, upper=upper_bound)

# Option 3: Transform to reduce impact
df['column_log'] = np.log1p(df['column'])  # Log transform
df['column_sqrt'] = np.sqrt(df['column'])  # Square root

# Option 4: Replace with median
df.loc[outliers_iqr.index, 'column'] = df['column'].median()

# Option 5: Flag outliers
df['is_outlier'] = ((df['column'] < lower_bound) | (df['column'] > upper_bound)).astype(int)
```

---

## Data Type Conversions

```python
# String to numeric
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')  # errors='coerce' converts invalid to NaN

# String to datetime
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

# Numeric to categorical
df['category'] = df['category_code'].astype('category')
df['age_group'] = pd.cut(df['age'], bins=[0, 18, 35, 50, 100], labels=['child', 'young', 'middle', 'senior'])

# Boolean conversion
df['is_active'] = df['is_active'].map({'Yes': True, 'No': False})
df['is_valid'] = df['status'] == 'valid'

# String cleaning before conversion
df['price'] = df['price'].str.replace('$', '').str.replace(',', '').astype(float)
df['percentage'] = df['percentage'].str.replace('%', '').astype(float) / 100
```

---

## Text Cleaning

```python
import re

# Basic cleaning
df['text'] = df['text'].str.lower()  # Lowercase
df['text'] = df['text'].str.strip()  # Remove leading/trailing spaces
df['text'] = df['text'].str.replace(r'\s+', ' ', regex=True)  # Multiple spaces to single

# Remove special characters
df['text'] = df['text'].str.replace(r'[^a-zA-Z0-9\s]', '', regex=True)

# Remove digits
df['text'] = df['text'].str.replace(r'\d+', '', regex=True)

# Extract patterns
df['email'] = df['text'].str.extract(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
df['phone'] = df['text'].str.extract(r'(\d{3}[-.]?\d{3}[-.]?\d{4})')

# Standardize categorical values
df['category'] = df['category'].str.lower().str.strip()
df['category'] = df['category'].replace({
    'nyc': 'new york',
    'la': 'los angeles',
    'sf': 'san francisco'
})
```

---

## Date/Time Handling

```python
# Parse dates
df['date'] = pd.to_datetime(df['date'])

# Extract components
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day'] = df['date'].dt.day
df['day_of_week'] = df['date'].dt.dayofweek
df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6])
df['quarter'] = df['date'].dt.quarter

# Time differences
df['days_since_event'] = (pd.Timestamp.now() - df['date']).dt.days

# Date arithmetic
df['date_plus_30'] = df['date'] + pd.Timedelta(days=30)

# Handling timezone
df['date_utc'] = df['date'].dt.tz_localize('UTC')
df['date_local'] = df['date_utc'].dt.tz_convert('America/New_York')

# Resample time series
df.set_index('date', inplace=True)
monthly = df.resample('M').sum()
weekly = df.resample('W').mean()
hourly = df.resample('H').count()
```

---

## Duplicate Management

```python
# Find duplicates
df.duplicated().sum()  # Count
df[df.duplicated()]  # Show duplicates
df[df.duplicated(keep=False)]  # Show all duplicate rows

# Check duplicates on specific columns
df.duplicated(subset=['email', 'phone']).sum()

# Remove duplicates
df.drop_duplicates(inplace=True)  # Keep first
df.drop_duplicates(keep='last', inplace=True)  # Keep last
df.drop_duplicates(subset=['email'], inplace=True)  # Based on specific columns

# Deduplication with aggregation
df.groupby('id').agg({
    'name': 'first',
    'amount': 'sum',
    'date': 'max'
}).reset_index()
```

---

## Validation Patterns

```python
# Validate email format
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
df['email_valid'] = df['email'].str.match(email_pattern)

# Validate phone number (US format)
phone_pattern = r'^\d{3}[-.]?\d{3}[-.]?\d{4}$'
df['phone_valid'] = df['phone'].str.match(phone_pattern)

# Validate date range
df['date_valid'] = (df['date'] >= '2020-01-01') & (df['date'] <= pd.Timestamp.now())

# Validate numeric range
df['age_valid'] = (df['age'] >= 0) & (df['age'] <= 120)

# Cross-field validation
df['valid'] = (df['end_date'] > df['start_date']) & (df['amount'] > 0)
```
