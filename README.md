# Ordering System

[ordering system source code](https://github.com/BSDSA-ISU/ordering-system-group-koishi)

![Reimu](https://media1.tenor.com/m/gc4ws16CrTYAAAAC/reimu-touhou.gif)

- [Ordering System](#ordering-system)
  - [Tasks](#tasks)
  - [System progress pictures](#system-progress-pictures)
- [3 METHODOLOGY](#3-methodology)
  - [3.1 Conceptual Framework](#31-conceptual-framework)
  - [3.2 Dataset Context and Description](#32-dataset-context-and-description)
    - [Data Dictionary](#data-dictionary)

## Tasks

- [Files](./sql_file/)

## System progress pictures

![image](./pictures/p1.png)

![image](./pictures/p2.png)

# 3 METHODOLOGY

This study adopts a supervised machine learning approach to examine student academic risk using student information, academic performance, homework, attendance, and teacher-parent communication records. The methodology follows a structured process consisting of data acquisition, data understanding, data preparation, exploratory analysis, model development, evaluation, and interpretation. The five datasets are integrated using their shared `Student_ID` identifier, while appropriate precautions are applied to prevent data leakage during model development.

## 3.1 Conceptual Framework

The conceptual framework presents the sequence of activities used to develop an academic risk classification model. The process begins with the acquisition of five related CSV datasets: student information, academic performance, homework records, attendance records, and teacher-parent communication records.

After acquisition, the datasets undergo initial inspection to determine their structure, variable types, record counts, missing values, duplicate entries, and inconsistencies. Data preparation follows, including standardization of categorical values, validation of numeric fields, date conversion, and integration through the shared `Student_ID` identifier. Relevant records are then transformed into an analytical dataset suitable for exploratory data analysis and classification.

For supervised learning, the proposed target variable is **Risk_Status**, which categorizes an observation as either At-Risk or Not At-Risk based on an institutionally approved academic performance threshold. The final examination score is used only to establish the target label and is excluded from the predictor variables to prevent direct target leakage.

The prepared observations are divided into training, validation, and testing subsets using a group-based splitting strategy based on `Student_ID`. This ensures that records belonging to the same student do not appear in different subsets. Data transformations that learn parameters from the dataset are fitted using the training subset and subsequently applied to the validation and testing subsets.

The training subset is used to develop the classification models, while the validation subset supports model selection and parameter tuning. The testing subset is reserved for the final evaluation. The resulting predictions are assessed using appropriate classification metrics, including accuracy, precision, recall, F1-score, and a confusion matrix. Finally, the results are interpreted to identify patterns associated with academic risk and discuss the potential usefulness and limitations of the findings.

**Figure 1. Workflow of the case study**

## 3.2 Dataset Context and Description

The study uses five related comma-separated values (CSV) files containing student-related educational records. The files are named `students.csv`, `performance.csv`, `homework.csv`, `attendance.csv`, and `teacher_parent_communication.csv`. These datasets share the `Student_ID` field, which serves as the common identifier for integrating records from the different sources.

The original creator or organization, official dataset title, source URL, collection context, and license or permission information have not yet been established from the supplied files. These details must be verified from the original provider before final manuscript submission. The five CSV files were supplied for this case study and were available for analysis on November 4, 2026. This date refers to the files' availability in the study workspace, not necessarily their original publication or collection date.

The initial dataset inventory contains **498,396 records across five files**, representing 12,156 unique student identifiers. The records are distributed as follows: 12,156 student records, 36,468 academic performance records, 60,780 homework records, 364,680 attendance records, and 24,312 teacher-parent communication records. These counts describe the original files before the completion of the final cleaning and integration process.

The five datasets have different units of observation. The student information file contains student-level records; the performance file contains student-subject records; the homework file contains assignment-level records; the attendance file contains student attendance records associated with dates and subjects; and the communication file contains individual communication records. Consequently, the records must be aggregated or matched at an appropriate analytical level before they are used together in a classification model.

The proposed analytical observation is a **student-subject record**, where the academic performance record provides the basis for the target label and relevant attendance and homework information can be associated with the corresponding student and subject. Student-level information may also be incorporated where appropriate. Communication records will only be included if their contents and timing are verified as meaningful and suitable for prediction.

The initial inventory identified 618 missing cells in the student information file, 290 exact duplicate rows in the attendance file, inconsistent attendance and homework status labels, 5,139 examination scores above 100, and 7,376 homework completion values below zero. These observations are treated as data quality issues requiring investigation during preprocessing. They are not automatically assumed to be valid or invalid without examining their definitions and context.

The initial dataset inventory is summarized below.

| Dataset                          | Original records |             Columns | Main observation unit |
| -------------------------------- | ---------------: | ------------------: | --------------------- |
| students.csv                     |           12,156 |                   5 | Student               |
| performance.csv                  |           36,468 |                   5 | Student-subject       |
| homework.csv                     |           60,780 |                   7 | Student-assignment    |
| attendance.csv                   |          364,680 |                   4 | Student-date-subject  |
| teacher_parent_communication.csv |           24,312 |                   4 | Communication record  |
| **Total**                        |      **498,396** | **25 across files** | Multiple levels       |

### Data Dictionary

The following table summarizes the variables available in the five source files.

| Dataset                      | Variables               | Description                             |
| ---------------------------- | ----------------------- | --------------------------------------- |
| Students                     | `Student_ID`            | Unique student identifier               |
|                              | `Full_Name`             | Student's recorded full name            |
|                              | `Date_of_Birth`         | Student's date of birth                 |
|                              | `Grade_Level`           | Student's recorded grade level          |
|                              | `Emergency_Contact`     | Recorded emergency contact information  |
| Performance                  | `Student_ID`            | Student identifier                      |
|                              | `Subject`               | Academic subject                        |
|                              | `Exam_Score`            | Recorded examination score              |
|                              | `Homework_Completion_%` | Recorded homework completion percentage |
|                              | `Teacher_Comments`      | Teacher-provided comments               |
| Homework                     | `Student_ID`            | Student identifier                      |
|                              | `Subject`               | Academic subject                        |
|                              | `Assignment_Name`       | Assignment identifier or name           |
|                              | `Due_Date`              | Assignment due date                     |
|                              | `Status`                | Recorded homework completion status     |
|                              | `Grade_Feedback`        | Recorded assignment feedback            |
|                              | `Guardian_Signature`    | Recorded guardian signature status      |
| Attendance                   | `Student_ID`            | Student identifier                      |
|                              | `Date`                  | Attendance record date                  |
|                              | `Subject`               | Academic subject                        |
|                              | `Attendance_Status`     | Recorded attendance status              |
| Teacher-Parent Communication | `Student_ID`            | Student identifier                      |
|                              | `Date`                  | Communication date                      |
|                              | `Message_Type`          | Type or direction of communication      |
|                              | `Message_Content`       | Recorded communication message          |

For the classification task, the proposed target variable is `Risk_Status`, a binary variable derived from `Exam_Score` using an approved academic performance threshold. A value below the threshold is assigned as At-Risk, while a value equal to or above the threshold is assigned as Not At-Risk. The threshold must be confirmed with the institution before the final target labels and class distribution are reported.

The final number of retained records, final predictor count, and target class distribution will be reported after data cleaning, integration, feature construction, and target validation. Identifying information such as student names and emergency contact details will not be used as model predictors. The student identifier will be retained only for record matching and group-based data splitting.
