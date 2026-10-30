from openpyxl import Workbook, load_workbook

from hw_tester.utils.generate_targets import add_di_data


def test_add_di_data_populates_ai_rows(tmp_path):
    path = tmp_path / "Target_J1.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Card", "Discrete Name"])
    worksheet.append(["C1", "AI_1"])
    worksheet.append(["2", "AI2"])
    worksheet.append(["3", "Power"])
    worksheet["J4"] = "10V"
    worksheet["L4"] = "Red"
    workbook.save(path)

    assert add_di_data(path) == 3

    worksheet = load_workbook(path).active
    assert worksheet["N2"].value == 1
    assert worksheet["R2"].value == "TBD"
    assert worksheet["T2"].value == "C1_AI1_10"
    assert worksheet["N3"].value == 1
    assert worksheet["R3"].value == "TBD"
    assert worksheet["T3"].value == "C2_AI2_10"
    assert worksheet["N4"].value == 10
    assert worksheet["O4"].value == "P"
