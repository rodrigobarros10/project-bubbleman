import numpy as np

class DataStructure:
    """
    Represents a data structure in terms of columns, rows, and data types.
    """

    def __init__(self, columns: dict, rows: list):
        """
        Initialize the data structure.
        :param columns: Dictionary of column names and their data types {column_name: data_type}.
        :param rows: List of row indexes (can be simple integers or IDs).
        """
        self.columns = columns  # {column_name: data_type}
        self.rows = rows  # [row_index_1, row_index_2, ...]


    def __init__(self, array_of_dicts):
        """
        Initialize the data structure from an array of dictionaries or numpy-like arrays.
        :param array_of_dicts: List of dictionaries or arrays where each row can have varying columns.
        """
        # Determine the union of all column names
        self.columns = self._extract_columns(array_of_dicts)

        # Create rows with consistent columns, filling missing values with None
        self.rows = self._normalize_rows(array_of_dicts, self.columns)

    def _extract_columns(self, array_of_dicts):
        """
        Extract all unique column names from the input.
        :param array_of_dicts: List of dictionaries or arrays.
        :return: Set of unique column names.
        """
        column_set = set()
        for row in array_of_dicts:
            column_set.update(row.keys())
        return sorted(column_set)  # Return a sorted list for consistent column order

    def _normalize_rows(self, array_of_dicts, columns):
        """
        Normalize rows to have all columns, filling missing values with None.
        :param array_of_dicts: List of dictionaries or arrays.
        :param columns: Complete set of column names.
        :return: List of rows with consistent columns.
        """
        normalized_rows = []
        for row in array_of_dicts:
            normalized_row = {col: row.get(col, None) for col in columns}
            normalized_rows.append(normalized_row)
        return normalized_rows

    def _infer_column_types(self):
        """
        Infer the data type for each column based on its values.
        :return: Dictionary of column names and their data types {column_name: data_type}.
        """
        column_types = {}
        for column in self.columns:
            column_values = [row[column] for row in self.rows if row[column] is not None]
            column_types[column] = self._infer_type_from_values(column_values)
        return column_types

    def _infer_type_from_values(self, values):
        """
        Infer the common data type for a list of values.
        :param values: List of values in a column.
        :return: Inferred data type.
        """
        if not values:
            return None  # No values, return None type
        types = set(map(type, values))
        return types

    def summarize(self):
        """
        Summarize the data structure into reduced information.
        :return: Dictionary summarizing column count, column names, row count, and data types.
        """
        return {
            "column_count": len(self.columns),
            "column_names": self.columns,
            "row_count": len(self.rows),
            "data_types": self.column_types
        }


    def summarize(self):
        """
        Summarize the data structure into reduced information.
        :return: Dictionary summarizing column count, column names, row count, and data types.
        """
        return {
            "column_count": len(self.columns),
            "column_names": list(self.columns.keys()),
            "row_count": len(self.rows),
            "data_types": list(set(self.columns.values()))  # Unique data types
        }


class DataTransformation:
    """
    Tracks a data transformation and its impact on a data structure.
    """

    def __init__(self, name: str, input_structure: DataStructure, output_structure: DataStructure):
        """
        Initialize the transformation.
        :param name: Name of the transformation (e.g., "melt", "filter").
        :param input_structure: The input data structure.
        :param output_structure: The resulting data structure after transformation.
        """
        self.name = name
        self.input_structure = input_structure
        self.output_structure = output_structure

    def summarize_changes(self):
        """
        Summarize changes caused by the transformation.
        :return: Dictionary describing changes to columns, rows, and data types.
        """
        input_summary = self.input_structure.summarize()
        output_summary = self.output_structure.summarize()

        # Calculate column changes
        added_columns = set(output_summary["column_names"]) - set(input_summary["column_names"])
        removed_columns = set(input_summary["column_names"]) - set(output_summary["column_names"])

        # Calculate row changes
        row_change = output_summary["row_count"] - input_summary["row_count"]

        # Calculate data type changes
        added_data_types = set(output_summary["data_types"]) - set(input_summary["data_types"])
        removed_data_types = set(input_summary["data_types"]) - set(output_summary["data_types"])

        return {
            "transformation_name": self.name,
            "column_changes": {
                "added": list(added_columns),
                "removed": list(removed_columns)
            },
            "row_change": row_change,  # Positive for rows added, negative for rows removed
            "data_type_changes": {
                "added": list(added_data_types),
                "removed": list(removed_data_types)
            }
        }
}
