# Usage

The order is filled via Google Spreadsheet in the following table:

|    Day    |  Total  |        Ann      |        Bob      |       Carl      |         |
| --------- | ------- | --------------- | --------------- | --------------- | ------- |
| Monday    |  TOTAL  | order |   sum   | order |   sum   | order |   sum   | ROW_SUM |
| Tuesday   |  TOTAL  | order |   sum   | order |   sum   | order |   sum   | ROW_SUM |
| Wednesday |  TOTAL  | order |   sum   | order |   sum   | order |   sum   | ROW_SUM |
| Thursday  |  TOTAL  | order |   sum   | order |   sum   | order |   sum   | ROW_SUM |
| Friday    |  TOTAL  | order |   sum   | order |   sum   | order |   sum   | ROW_SUM |
|           | COL_SUM |       | COL_SUM |       | COL_SUM |       | COL_SUM |         |

* `order` is a comma-separated list of indices: 1,2,8;
* repetitions are allowed: 1,1,3;
* each sum column is formatted to be integer numbers;
* `Total` column is used to track minimal order sum (some catering services have such limitations);
* `COL_SUM`s can be used in such scenario: each week a certain persion is responsible for payments and at the end of the week it's easy to see each person's "debt".

# Development

Current version assumes that spreadsheet has public link and that `chromedriver` drive is executable (`chmod +x`).
