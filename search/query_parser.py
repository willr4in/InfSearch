# search/query_parser.py
import re

class QueryParser:
    """
    A simple boolean query parser that converts infix queries to postfix (Reverse Polish Notation).
    Supports AND, OR, NOT operators and parentheses.
    """
    PRECEDENCE = {'NOT': 3, 'AND': 2, 'OR': 1}

    def _tokenize(self, query: str):
        # Add spaces around parentheses to ensure they are tokenized correctly
        query = query.replace('(', ' ( ').replace(')', ' ) ')
        # Normalize operators to uppercase
        query = re.sub(r'\b(and|or|not)\b', lambda m: m.group(1).upper(), query, flags=re.IGNORECASE)
        return query.split()

    def to_postfix(self, query: str):
        """
        Converts an infix boolean query to postfix (RPN).
        Example: "a AND (b OR c)" -> ["a", "b", "c", "OR", "AND"]
        """
        output = []
        operators = []
        tokens = self._tokenize(query)

        for token in tokens:
            if token in self.PRECEDENCE:
                while (operators and operators[-1] != '(' and
                       self.PRECEDENCE.get(operators[-1], 0) >= self.PRECEDENCE.get(token, 0)):
                    output.append(operators.pop())
                operators.append(token)
            elif token == '(':
                operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    output.append(operators.pop())
                if operators and operators[-1] == '(':
                    operators.pop()  # Pop '('
                else:
                    raise ValueError("Mismatched parentheses")
            else: # Operand
                output.append(token.lower())
        
        while operators:
            if operators[-1] == '(':
                raise ValueError("Mismatched parentheses")
            output.append(operators.pop())
            
        return output

