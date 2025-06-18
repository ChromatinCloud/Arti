#!/bin/bash
# Test Commands for Annotation Engine VCF Files
# Generated 2025-06-18
# This script contains annotation-engine commands for all 94 test VCF files

set -e  # Exit on any error

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Annotation Engine Test Commands${NC}"
echo "=================================="
echo "Total test files: 94"
echo "Use: bash test_commands.sh [test_number]"
echo "Example: bash test_commands.sh 1  # Run test 1"
echo "         bash test_commands.sh    # Show all commands"
echo ""

# Function to run a specific test
run_test() {
    local test_num=$1
    local cmd=$2
    echo -e "${YELLOW}Running Test $test_num:${NC}"
    echo "$cmd"
    echo ""
    eval "$cmd"
}

# If test number provided, run that specific test
if [ $# -eq 1 ]; then
    case $1 in

# ===== BREAST CANCER TESTS =====

1)
run_test 1 'poetry run annotation-engine \
    --tumor-vcf example_input/breast_tumor_normal_10vars.vcf \
    --case-uid "BREAST_TN_001" \
    --patient-uid "PATIENT_001" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_tn_10vars'
;;

2)
run_test 2 'poetry run annotation-engine \
    --tumor-vcf example_input/breast_tumor_normal_100vars.vcf \
    --case-uid "BREAST_TN_002" \
    --patient-uid "PATIENT_002" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_tn_100vars'
;;

3)
run_test 3 'poetry run annotation-engine \
    --tumor-vcf example_input/breast_tumor_normal_1000vars.vcf \
    --case-uid "BREAST_TN_003" \
    --patient-uid "PATIENT_003" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_tn_1000vars'
;;

4)
run_test 4 'poetry run annotation-engine \
    --tumor-vcf example_input/breast_tumor_normal_10000vars.vcf \
    --case-uid "BREAST_TN_004" \
    --patient-uid "PATIENT_004" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_tn_10000vars'
;;

5)
run_test 5 'poetry run annotation-engine \
    --input example_input/breast_tumor_only_10vars.vcf \
    --case-uid "BREAST_TO_001" \
    --patient-uid "PATIENT_005" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_to_10vars'
;;

6)
run_test 6 'poetry run annotation-engine \
    --input example_input/breast_tumor_only_100vars.vcf \
    --case-uid "BREAST_TO_002" \
    --patient-uid "PATIENT_006" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_to_100vars'
;;

7)
run_test 7 'poetry run annotation-engine \
    --input example_input/breast_tumor_only_1000vars.vcf \
    --case-uid "BREAST_TO_003" \
    --patient-uid "PATIENT_007" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_to_1000vars'
;;

8)
run_test 8 'poetry run annotation-engine \
    --input example_input/breast_tumor_only_10000vars.vcf \
    --case-uid "BREAST_TO_004" \
    --patient-uid "PATIENT_008" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/breast_to_10000vars'
;;

# ===== LUNG ADENOCARCINOMA TESTS =====

9)
run_test 9 'poetry run annotation-engine \
    --tumor-vcf example_input/lung_tumor_normal_10vars.vcf \
    --case-uid "LUNG_TN_001" \
    --patient-uid "PATIENT_009" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_tn_10vars'
;;

10)
run_test 10 'poetry run annotation-engine \
    --tumor-vcf example_input/lung_tumor_normal_100vars.vcf \
    --case-uid "LUNG_TN_002" \
    --patient-uid "PATIENT_010" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_tn_100vars'
;;

11)
run_test 11 'poetry run annotation-engine \
    --tumor-vcf example_input/lung_tumor_normal_1000vars.vcf \
    --case-uid "LUNG_TN_003" \
    --patient-uid "PATIENT_011" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_tn_1000vars'
;;

12)
run_test 12 'poetry run annotation-engine \
    --tumor-vcf example_input/lung_tumor_normal_10000vars.vcf \
    --case-uid "LUNG_TN_004" \
    --patient-uid "PATIENT_012" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_tn_10000vars'
;;

13)
run_test 13 'poetry run annotation-engine \
    --input example_input/lung_tumor_only_10vars.vcf \
    --case-uid "LUNG_TO_001" \
    --patient-uid "PATIENT_013" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_to_10vars'
;;

14)
run_test 14 'poetry run annotation-engine \
    --input example_input/lung_tumor_only_100vars.vcf \
    --case-uid "LUNG_TO_002" \
    --patient-uid "PATIENT_014" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_to_100vars'
;;

15)
run_test 15 'poetry run annotation-engine \
    --input example_input/lung_tumor_only_1000vars.vcf \
    --case-uid "LUNG_TO_003" \
    --patient-uid "PATIENT_015" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_to_1000vars'
;;

16)
run_test 16 'poetry run annotation-engine \
    --input example_input/lung_tumor_only_10000vars.vcf \
    --case-uid "LUNG_TO_004" \
    --patient-uid "PATIENT_016" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/lung_to_10000vars'
;;

# ===== COLORECTAL CANCER TESTS =====

17)
run_test 17 'poetry run annotation-engine \
    --tumor-vcf example_input/colorectal_tumor_normal_10vars.vcf \
    --case-uid "CRC_TN_001" \
    --patient-uid "PATIENT_017" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_tn_10vars'
;;

18)
run_test 18 'poetry run annotation-engine \
    --tumor-vcf example_input/colorectal_tumor_normal_100vars.vcf \
    --case-uid "CRC_TN_002" \
    --patient-uid "PATIENT_018" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_tn_100vars'
;;

19)
run_test 19 'poetry run annotation-engine \
    --tumor-vcf example_input/colorectal_tumor_normal_1000vars.vcf \
    --case-uid "CRC_TN_003" \
    --patient-uid "PATIENT_019" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_tn_1000vars'
;;

20)
run_test 20 'poetry run annotation-engine \
    --tumor-vcf example_input/colorectal_tumor_normal_10000vars.vcf \
    --case-uid "CRC_TN_004" \
    --patient-uid "PATIENT_020" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_tn_10000vars'
;;

21)
run_test 21 'poetry run annotation-engine \
    --input example_input/colorectal_tumor_only_10vars.vcf \
    --case-uid "CRC_TO_001" \
    --patient-uid "PATIENT_021" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_to_10vars'
;;

22)
run_test 22 'poetry run annotation-engine \
    --input example_input/colorectal_tumor_only_100vars.vcf \
    --case-uid "CRC_TO_002" \
    --patient-uid "PATIENT_022" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_to_100vars'
;;

23)
run_test 23 'poetry run annotation-engine \
    --input example_input/colorectal_tumor_only_1000vars.vcf \
    --case-uid "CRC_TO_003" \
    --patient-uid "PATIENT_023" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_to_1000vars'
;;

24)
run_test 24 'poetry run annotation-engine \
    --input example_input/colorectal_tumor_only_10000vars.vcf \
    --case-uid "CRC_TO_004" \
    --patient-uid "PATIENT_024" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/crc_to_10000vars'
;;

# ===== MELANOMA TESTS =====

25)
run_test 25 'poetry run annotation-engine \
    --tumor-vcf example_input/melanoma_tumor_normal_10vars.vcf \
    --case-uid "MEL_TN_001" \
    --patient-uid "PATIENT_025" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_tn_10vars'
;;

26)
run_test 26 'poetry run annotation-engine \
    --tumor-vcf example_input/melanoma_tumor_normal_100vars.vcf \
    --case-uid "MEL_TN_002" \
    --patient-uid "PATIENT_026" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_tn_100vars'
;;

27)
run_test 27 'poetry run annotation-engine \
    --tumor-vcf example_input/melanoma_tumor_normal_1000vars.vcf \
    --case-uid "MEL_TN_003" \
    --patient-uid "PATIENT_027" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_tn_1000vars'
;;

28)
run_test 28 'poetry run annotation-engine \
    --tumor-vcf example_input/melanoma_tumor_normal_10000vars.vcf \
    --case-uid "MEL_TN_004" \
    --patient-uid "PATIENT_028" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_tn_10000vars'
;;

29)
run_test 29 'poetry run annotation-engine \
    --input example_input/melanoma_tumor_only_10vars.vcf \
    --case-uid "MEL_TO_001" \
    --patient-uid "PATIENT_029" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_to_10vars'
;;

30)
run_test 30 'poetry run annotation-engine \
    --input example_input/melanoma_tumor_only_100vars.vcf \
    --case-uid "MEL_TO_002" \
    --patient-uid "PATIENT_030" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_to_100vars'
;;

31)
run_test 31 'poetry run annotation-engine \
    --input example_input/melanoma_tumor_only_1000vars.vcf \
    --case-uid "MEL_TO_003" \
    --patient-uid "PATIENT_031" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_to_1000vars'
;;

32)
run_test 32 'poetry run annotation-engine \
    --input example_input/melanoma_tumor_only_10000vars.vcf \
    --case-uid "MEL_TO_004" \
    --patient-uid "PATIENT_032" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/mel_to_10000vars'
;;

# ===== OVARIAN CANCER TESTS =====

33)
run_test 33 'poetry run annotation-engine \
    --tumor-vcf example_input/ovarian_tumor_normal_10vars.vcf \
    --case-uid "OV_TN_001" \
    --patient-uid "PATIENT_033" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_tn_10vars'
;;

34)
run_test 34 'poetry run annotation-engine \
    --tumor-vcf example_input/ovarian_tumor_normal_100vars.vcf \
    --case-uid "OV_TN_002" \
    --patient-uid "PATIENT_034" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_tn_100vars'
;;

35)
run_test 35 'poetry run annotation-engine \
    --tumor-vcf example_input/ovarian_tumor_normal_1000vars.vcf \
    --case-uid "OV_TN_003" \
    --patient-uid "PATIENT_035" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_tn_1000vars'
;;

36)
run_test 36 'poetry run annotation-engine \
    --tumor-vcf example_input/ovarian_tumor_normal_10000vars.vcf \
    --case-uid "OV_TN_004" \
    --patient-uid "PATIENT_036" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_tn_10000vars'
;;

37)
run_test 37 'poetry run annotation-engine \
    --input example_input/ovarian_tumor_only_10vars.vcf \
    --case-uid "OV_TO_001" \
    --patient-uid "PATIENT_037" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_to_10vars'
;;

38)
run_test 38 'poetry run annotation-engine \
    --input example_input/ovarian_tumor_only_100vars.vcf \
    --case-uid "OV_TO_002" \
    --patient-uid "PATIENT_038" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_to_100vars'
;;

39)
run_test 39 'poetry run annotation-engine \
    --input example_input/ovarian_tumor_only_1000vars.vcf \
    --case-uid "OV_TO_003" \
    --patient-uid "PATIENT_039" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_to_1000vars'
;;

40)
run_test 40 'poetry run annotation-engine \
    --input example_input/ovarian_tumor_only_10000vars.vcf \
    --case-uid "OV_TO_004" \
    --patient-uid "PATIENT_040" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/ov_to_10000vars'
;;

# ===== PANCREATIC CANCER TESTS =====

41)
run_test 41 'poetry run annotation-engine \
    --tumor-vcf example_input/pancreatic_tumor_normal_10vars.vcf \
    --case-uid "PANC_TN_001" \
    --patient-uid "PATIENT_041" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_tn_10vars'
;;

42)
run_test 42 'poetry run annotation-engine \
    --tumor-vcf example_input/pancreatic_tumor_normal_100vars.vcf \
    --case-uid "PANC_TN_002" \
    --patient-uid "PATIENT_042" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_tn_100vars'
;;

43)
run_test 43 'poetry run annotation-engine \
    --tumor-vcf example_input/pancreatic_tumor_normal_1000vars.vcf \
    --case-uid "PANC_TN_003" \
    --patient-uid "PATIENT_043" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_tn_1000vars'
;;

44)
run_test 44 'poetry run annotation-engine \
    --tumor-vcf example_input/pancreatic_tumor_normal_10000vars.vcf \
    --case-uid "PANC_TN_004" \
    --patient-uid "PATIENT_044" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_tn_10000vars'
;;

45)
run_test 45 'poetry run annotation-engine \
    --input example_input/pancreatic_tumor_only_10vars.vcf \
    --case-uid "PANC_TO_001" \
    --patient-uid "PATIENT_045" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_to_10vars'
;;

46)
run_test 46 'poetry run annotation-engine \
    --input example_input/pancreatic_tumor_only_100vars.vcf \
    --case-uid "PANC_TO_002" \
    --patient-uid "PATIENT_046" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_to_100vars'
;;

47)
run_test 47 'poetry run annotation-engine \
    --input example_input/pancreatic_tumor_only_1000vars.vcf \
    --case-uid "PANC_TO_003" \
    --patient-uid "PATIENT_047" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_to_1000vars'
;;

48)
run_test 48 'poetry run annotation-engine \
    --input example_input/pancreatic_tumor_only_10000vars.vcf \
    --case-uid "PANC_TO_004" \
    --patient-uid "PATIENT_048" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/panc_to_10000vars'
;;

# ===== PROSTATE CANCER TESTS =====

49)
run_test 49 'poetry run annotation-engine \
    --tumor-vcf example_input/prostate_tumor_normal_10vars.vcf \
    --case-uid "PROST_TN_001" \
    --patient-uid "PATIENT_049" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_tn_10vars'
;;

50)
run_test 50 'poetry run annotation-engine \
    --tumor-vcf example_input/prostate_tumor_normal_100vars.vcf \
    --case-uid "PROST_TN_002" \
    --patient-uid "PATIENT_050" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_tn_100vars'
;;

51)
run_test 51 'poetry run annotation-engine \
    --tumor-vcf example_input/prostate_tumor_normal_1000vars.vcf \
    --case-uid "PROST_TN_003" \
    --patient-uid "PATIENT_051" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_tn_1000vars'
;;

52)
run_test 52 'poetry run annotation-engine \
    --tumor-vcf example_input/prostate_tumor_normal_10000vars.vcf \
    --case-uid "PROST_TN_004" \
    --patient-uid "PATIENT_052" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_tn_10000vars'
;;

53)
run_test 53 'poetry run annotation-engine \
    --input example_input/prostate_tumor_only_10vars.vcf \
    --case-uid "PROST_TO_001" \
    --patient-uid "PATIENT_053" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_to_10vars'
;;

54)
run_test 54 'poetry run annotation-engine \
    --input example_input/prostate_tumor_only_100vars.vcf \
    --case-uid "PROST_TO_002" \
    --patient-uid "PATIENT_054" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_to_100vars'
;;

55)
run_test 55 'poetry run annotation-engine \
    --input example_input/prostate_tumor_only_1000vars.vcf \
    --case-uid "PROST_TO_003" \
    --patient-uid "PATIENT_055" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_to_1000vars'
;;

56)
run_test 56 'poetry run annotation-engine \
    --input example_input/prostate_tumor_only_10000vars.vcf \
    --case-uid "PROST_TO_004" \
    --patient-uid "PATIENT_056" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/prost_to_10000vars'
;;

# ===== GLIOBLASTOMA TESTS =====

57)
run_test 57 'poetry run annotation-engine \
    --tumor-vcf example_input/glioblastoma_tumor_normal_10vars.vcf \
    --case-uid "GBM_TN_001" \
    --patient-uid "PATIENT_057" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_tn_10vars'
;;

58)
run_test 58 'poetry run annotation-engine \
    --tumor-vcf example_input/glioblastoma_tumor_normal_100vars.vcf \
    --case-uid "GBM_TN_002" \
    --patient-uid "PATIENT_058" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_tn_100vars'
;;

59)
run_test 59 'poetry run annotation-engine \
    --tumor-vcf example_input/glioblastoma_tumor_normal_1000vars.vcf \
    --case-uid "GBM_TN_003" \
    --patient-uid "PATIENT_059" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_tn_1000vars'
;;

60)
run_test 60 'poetry run annotation-engine \
    --tumor-vcf example_input/glioblastoma_tumor_normal_10000vars.vcf \
    --case-uid "GBM_TN_004" \
    --patient-uid "PATIENT_060" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_tn_10000vars'
;;

61)
run_test 61 'poetry run annotation-engine \
    --input example_input/glioblastoma_tumor_only_10vars.vcf \
    --case-uid "GBM_TO_001" \
    --patient-uid "PATIENT_061" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_to_10vars'
;;

62)
run_test 62 'poetry run annotation-engine \
    --input example_input/glioblastoma_tumor_only_100vars.vcf \
    --case-uid "GBM_TO_002" \
    --patient-uid "PATIENT_062" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_to_100vars'
;;

63)
run_test 63 'poetry run annotation-engine \
    --input example_input/glioblastoma_tumor_only_1000vars.vcf \
    --case-uid "GBM_TO_003" \
    --patient-uid "PATIENT_063" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_to_1000vars'
;;

64)
run_test 64 'poetry run annotation-engine \
    --input example_input/glioblastoma_tumor_only_10000vars.vcf \
    --case-uid "GBM_TO_004" \
    --patient-uid "PATIENT_064" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/gbm_to_10000vars'
;;

# ===== ACUTE MYELOID LEUKEMIA TESTS =====

65)
run_test 65 'poetry run annotation-engine \
    --tumor-vcf example_input/aml_tumor_normal_10vars.vcf \
    --case-uid "AML_TN_001" \
    --patient-uid "PATIENT_065" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_tn_10vars'
;;

66)
run_test 66 'poetry run annotation-engine \
    --tumor-vcf example_input/aml_tumor_normal_100vars.vcf \
    --case-uid "AML_TN_002" \
    --patient-uid "PATIENT_066" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_tn_100vars'
;;

67)
run_test 67 'poetry run annotation-engine \
    --tumor-vcf example_input/aml_tumor_normal_1000vars.vcf \
    --case-uid "AML_TN_003" \
    --patient-uid "PATIENT_067" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_tn_1000vars'
;;

68)
run_test 68 'poetry run annotation-engine \
    --tumor-vcf example_input/aml_tumor_normal_10000vars.vcf \
    --case-uid "AML_TN_004" \
    --patient-uid "PATIENT_068" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_tn_10000vars'
;;

69)
run_test 69 'poetry run annotation-engine \
    --input example_input/aml_tumor_only_10vars.vcf \
    --case-uid "AML_TO_001" \
    --patient-uid "PATIENT_069" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_to_10vars'
;;

70)
run_test 70 'poetry run annotation-engine \
    --input example_input/aml_tumor_only_100vars.vcf \
    --case-uid "AML_TO_002" \
    --patient-uid "PATIENT_070" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_to_100vars'
;;

71)
run_test 71 'poetry run annotation-engine \
    --input example_input/aml_tumor_only_1000vars.vcf \
    --case-uid "AML_TO_003" \
    --patient-uid "PATIENT_071" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_to_1000vars'
;;

72)
run_test 72 'poetry run annotation-engine \
    --input example_input/aml_tumor_only_10000vars.vcf \
    --case-uid "AML_TO_004" \
    --patient-uid "PATIENT_072" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/aml_to_10000vars'
;;

# ===== MIXED CANCER TYPE TESTS =====

73)
run_test 73 'poetry run annotation-engine \
    --tumor-vcf example_input/mixed_tumor_normal_10vars.vcf \
    --case-uid "MIXED_TN_001" \
    --patient-uid "PATIENT_073" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_tn_10vars'
;;

74)
run_test 74 'poetry run annotation-engine \
    --tumor-vcf example_input/mixed_tumor_normal_100vars.vcf \
    --case-uid "MIXED_TN_002" \
    --patient-uid "PATIENT_074" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_tn_100vars'
;;

75)
run_test 75 'poetry run annotation-engine \
    --tumor-vcf example_input/mixed_tumor_normal_1000vars.vcf \
    --case-uid "MIXED_TN_003" \
    --patient-uid "PATIENT_075" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_tn_1000vars'
;;

76)
run_test 76 'poetry run annotation-engine \
    --tumor-vcf example_input/mixed_tumor_normal_10000vars.vcf \
    --case-uid "MIXED_TN_004" \
    --patient-uid "PATIENT_076" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_tn_10000vars'
;;

77)
run_test 77 'poetry run annotation-engine \
    --input example_input/mixed_tumor_only_10vars.vcf \
    --case-uid "MIXED_TO_001" \
    --patient-uid "PATIENT_077" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_to_10vars'
;;

78)
run_test 78 'poetry run annotation-engine \
    --input example_input/mixed_tumor_only_100vars.vcf \
    --case-uid "MIXED_TO_002" \
    --patient-uid "PATIENT_078" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_to_100vars'
;;

79)
run_test 79 'poetry run annotation-engine \
    --input example_input/mixed_tumor_only_1000vars.vcf \
    --case-uid "MIXED_TO_003" \
    --patient-uid "PATIENT_079" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_to_1000vars'
;;

80)
run_test 80 'poetry run annotation-engine \
    --input example_input/mixed_tumor_only_10000vars.vcf \
    --case-uid "MIXED_TO_004" \
    --patient-uid "PATIENT_080" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --output results/mixed_to_10000vars'
;;

# ===== SPECIAL VARIANT TYPE TESTS =====

81)
run_test 81 'poetry run annotation-engine \
    --input example_input/snv_only_test_100vars.vcf \
    --case-uid "SNV_TEST_001" \
    --patient-uid "PATIENT_081" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/snv_only_100vars'
;;

82)
run_test 82 'poetry run annotation-engine \
    --input example_input/indel_only_test_100vars.vcf \
    --case-uid "INDEL_TEST_001" \
    --patient-uid "PATIENT_082" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/indel_only_100vars'
;;

83)
run_test 83 'poetry run annotation-engine \
    --input example_input/cnv_only_test_50vars.vcf \
    --case-uid "CNV_TEST_001" \
    --patient-uid "PATIENT_083" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/cnv_only_50vars'
;;

84)
run_test 84 'poetry run annotation-engine \
    --input example_input/sv_only_test_25vars.vcf \
    --case-uid "SV_TEST_001" \
    --patient-uid "PATIENT_084" \
    --cancer-type ovarian_cancer \
    --tissue-type primary_tumor \
    --output results/sv_only_25vars'
;;

# ===== CLINVAR SIGNIFICANCE LEVEL TESTS =====

85)
run_test 85 'poetry run annotation-engine \
    --input example_input/pathogenic_variants_50vars.vcf \
    --case-uid "PATH_TEST_001" \
    --patient-uid "PATIENT_085" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/pathogenic_50vars'
;;

86)
run_test 86 'poetry run annotation-engine \
    --input example_input/likely_pathogenic_variants_50vars.vcf \
    --case-uid "LP_TEST_001" \
    --patient-uid "PATIENT_086" \
    --cancer-type pancreatic_cancer \
    --tissue-type primary_tumor \
    --output results/likely_pathogenic_50vars'
;;

87)
run_test 87 'poetry run annotation-engine \
    --input example_input/vus_variants_100vars.vcf \
    --case-uid "VUS_TEST_001" \
    --patient-uid "PATIENT_087" \
    --cancer-type prostate_cancer \
    --tissue-type primary_tumor \
    --output results/vus_100vars'
;;

88)
run_test 88 'poetry run annotation-engine \
    --input example_input/likely_benign_variants_100vars.vcf \
    --case-uid "LB_TEST_001" \
    --patient-uid "PATIENT_088" \
    --cancer-type glioblastoma \
    --tissue-type primary_tumor \
    --output results/likely_benign_100vars'
;;

89)
run_test 89 'poetry run annotation-engine \
    --input example_input/benign_variants_100vars.vcf \
    --case-uid "BEN_TEST_001" \
    --patient-uid "PATIENT_089" \
    --cancer-type acute_myeloid_leukemia \
    --tissue-type primary_tumor \
    --output results/benign_100vars'
;;

# ===== ONCOKB EVIDENCE LEVEL TESTS =====

90)
run_test 90 'poetry run annotation-engine \
    --input example_input/oncokb_level1_variants_25vars.vcf \
    --case-uid "OKBL1_TEST_001" \
    --patient-uid "PATIENT_090" \
    --cancer-type lung_adenocarcinoma \
    --tissue-type primary_tumor \
    --output results/oncokb_level1_25vars'
;;

91)
run_test 91 'poetry run annotation-engine \
    --input example_input/oncokb_level2_variants_30vars.vcf \
    --case-uid "OKBL2_TEST_001" \
    --patient-uid "PATIENT_091" \
    --cancer-type breast_cancer \
    --tissue-type primary_tumor \
    --output results/oncokb_level2_30vars'
;;

92)
run_test 92 'poetry run annotation-engine \
    --input example_input/oncokb_level3_variants_35vars.vcf \
    --case-uid "OKBL3_TEST_001" \
    --patient-uid "PATIENT_092" \
    --cancer-type colorectal_cancer \
    --tissue-type primary_tumor \
    --output results/oncokb_level3_35vars'
;;

93)
run_test 93 'poetry run annotation-engine \
    --input example_input/oncokb_level4_variants_40vars.vcf \
    --case-uid "OKBL4_TEST_001" \
    --patient-uid "PATIENT_093" \
    --cancer-type melanoma \
    --tissue-type primary_tumor \
    --output results/oncokb_level4_40vars'
;;

94)
run_test 94 'poetry run annotation-engine \
    --input example_input/comprehensive_test_all_features_500vars.vcf \
    --case-uid "COMPREHENSIVE_001" \
    --patient-uid "PATIENT_094" \
    --cancer-type other \
    --tissue-type primary_tumor \
    --tumor-purity 0.75 \
    --verbose \
    --output results/comprehensive_500vars'
;;

    *)
        echo -e "${RED}Invalid test number. Valid range: 1-94${NC}"
        exit 1
        ;;
    esac
    exit 0
fi

# If no argument provided, show all available commands
echo -e "${YELLOW}Available Tests:${NC}"
echo ""

echo "BREAST CANCER TESTS (1-8):"
echo "1.  Breast Tumor-Normal 10 variants"
echo "2.  Breast Tumor-Normal 100 variants"
echo "3.  Breast Tumor-Normal 1000 variants"
echo "4.  Breast Tumor-Normal 10000 variants"
echo "5.  Breast Tumor-Only 10 variants"
echo "6.  Breast Tumor-Only 100 variants"
echo "7.  Breast Tumor-Only 1000 variants"
echo "8.  Breast Tumor-Only 10000 variants"
echo ""

echo "LUNG ADENOCARCINOMA TESTS (9-16):"
echo "9.  Lung Tumor-Normal 10 variants"
echo "10. Lung Tumor-Normal 100 variants"
echo "11. Lung Tumor-Normal 1000 variants"
echo "12. Lung Tumor-Normal 10000 variants"
echo "13. Lung Tumor-Only 10 variants"
echo "14. Lung Tumor-Only 100 variants"
echo "15. Lung Tumor-Only 1000 variants"
echo "16. Lung Tumor-Only 10000 variants"
echo ""

echo "COLORECTAL CANCER TESTS (17-24):"
echo "17. CRC Tumor-Normal 10 variants"
echo "18. CRC Tumor-Normal 100 variants"
echo "19. CRC Tumor-Normal 1000 variants"
echo "20. CRC Tumor-Normal 10000 variants"
echo "21. CRC Tumor-Only 10 variants"
echo "22. CRC Tumor-Only 100 variants"
echo "23. CRC Tumor-Only 1000 variants"
echo "24. CRC Tumor-Only 10000 variants"
echo ""

echo "MELANOMA TESTS (25-32):"
echo "25. Melanoma Tumor-Normal 10 variants"
echo "26. Melanoma Tumor-Normal 100 variants"
echo "27. Melanoma Tumor-Normal 1000 variants"
echo "28. Melanoma Tumor-Normal 10000 variants"
echo "29. Melanoma Tumor-Only 10 variants"
echo "30. Melanoma Tumor-Only 100 variants"
echo "31. Melanoma Tumor-Only 1000 variants"
echo "32. Melanoma Tumor-Only 10000 variants"
echo ""

echo "OVARIAN CANCER TESTS (33-40):"
echo "33. Ovarian Tumor-Normal 10 variants"
echo "34. Ovarian Tumor-Normal 100 variants"
echo "35. Ovarian Tumor-Normal 1000 variants"
echo "36. Ovarian Tumor-Normal 10000 variants"
echo "37. Ovarian Tumor-Only 10 variants"
echo "38. Ovarian Tumor-Only 100 variants"
echo "39. Ovarian Tumor-Only 1000 variants"
echo "40. Ovarian Tumor-Only 10000 variants"
echo ""

echo "PANCREATIC CANCER TESTS (41-48):"
echo "41. Pancreatic Tumor-Normal 10 variants"
echo "42. Pancreatic Tumor-Normal 100 variants"
echo "43. Pancreatic Tumor-Normal 1000 variants"
echo "44. Pancreatic Tumor-Normal 10000 variants"
echo "45. Pancreatic Tumor-Only 10 variants"
echo "46. Pancreatic Tumor-Only 100 variants"
echo "47. Pancreatic Tumor-Only 1000 variants"
echo "48. Pancreatic Tumor-Only 10000 variants"
echo ""

echo "PROSTATE CANCER TESTS (49-56):"
echo "49. Prostate Tumor-Normal 10 variants"
echo "50. Prostate Tumor-Normal 100 variants"
echo "51. Prostate Tumor-Normal 1000 variants"
echo "52. Prostate Tumor-Normal 10000 variants"
echo "53. Prostate Tumor-Only 10 variants"
echo "54. Prostate Tumor-Only 100 variants"
echo "55. Prostate Tumor-Only 1000 variants"
echo "56. Prostate Tumor-Only 10000 variants"
echo ""

echo "GLIOBLASTOMA TESTS (57-64):"
echo "57. GBM Tumor-Normal 10 variants"
echo "58. GBM Tumor-Normal 100 variants"
echo "59. GBM Tumor-Normal 1000 variants"
echo "60. GBM Tumor-Normal 10000 variants"
echo "61. GBM Tumor-Only 10 variants"
echo "62. GBM Tumor-Only 100 variants"
echo "63. GBM Tumor-Only 1000 variants"
echo "64. GBM Tumor-Only 10000 variants"
echo ""

echo "ACUTE MYELOID LEUKEMIA TESTS (65-72):"
echo "65. AML Tumor-Normal 10 variants"
echo "66. AML Tumor-Normal 100 variants"
echo "67. AML Tumor-Normal 1000 variants"
echo "68. AML Tumor-Normal 10000 variants"
echo "69. AML Tumor-Only 10 variants"
echo "70. AML Tumor-Only 100 variants"
echo "71. AML Tumor-Only 1000 variants"
echo "72. AML Tumor-Only 10000 variants"
echo ""

echo "MIXED CANCER TYPE TESTS (73-80):"
echo "73. Mixed Tumor-Normal 10 variants"
echo "74. Mixed Tumor-Normal 100 variants"
echo "75. Mixed Tumor-Normal 1000 variants"
echo "76. Mixed Tumor-Normal 10000 variants"
echo "77. Mixed Tumor-Only 10 variants"
echo "78. Mixed Tumor-Only 100 variants"
echo "79. Mixed Tumor-Only 1000 variants"
echo "80. Mixed Tumor-Only 10000 variants"
echo ""

echo "VARIANT TYPE SPECIFIC TESTS (81-84):"
echo "81. SNV-only test (100 variants)"
echo "82. Indel-only test (100 variants)"
echo "83. CNV-only test (50 variants)"
echo "84. SV-only test (25 variants)"
echo ""

echo "CLINVAR SIGNIFICANCE TESTS (85-89):"
echo "85. Pathogenic variants (50 variants)"
echo "86. Likely pathogenic variants (50 variants)"
echo "87. VUS variants (100 variants)"
echo "88. Likely benign variants (100 variants)"
echo "89. Benign variants (100 variants)"
echo ""

echo "ONCOKB EVIDENCE LEVEL TESTS (90-94):"
echo "90. OncoKB Level 1 variants (25 variants)"
echo "91. OncoKB Level 2 variants (30 variants)"
echo "92. OncoKB Level 3 variants (35 variants)"
echo "93. OncoKB Level 4 variants (40 variants)"
echo "94. Comprehensive test (500 variants)"
echo ""

echo -e "${GREEN}Usage Examples:${NC}"
echo "bash test_commands.sh 1      # Run breast cancer tumor-normal 10 variants"
echo "bash test_commands.sh 94     # Run comprehensive test"
echo "bash test_commands.sh        # Show this help menu"