from llvmlite import ir
from ast2 import Type


def generate_struct_declaration(self, node):
    """
    Process a struct declaration and register it with the type system
    """
    # Create a dictionary to store field types
    field_types = {}
    
    # Process each field
    for field in node.fields:
        field_type = field.type
        for field_name in field.names:
            field_types[field_name] = field_type
    
    # Register the struct type with Type system
    Type.register_struct_type(node.name, field_types)


def generate_declare_struct(self, node):
    """
    Generate code for struct instance declaration. This will be similar to declare_assign
    but specialized for structs
    """
    struct_type_name = node.struct_type
    
    # Check if struct type exists
    if not Type.is_struct_type(struct_type_name):
        raise ValueError(f"Unknown struct type: {struct_type_name}")
    
    # For simplicity, we'll represent a struct as an i64* pointer 
    # and use GEP to access its fields
    if self.builder is None:
        # Global structs - treated as a pointer to memory
        # This is a simplified implementation that dodges the struct constant issues
        var_ptr = ir.GlobalVariable(self.module, ir.IntType(64), name=node.name)
        var_ptr.initializer = ir.Constant(ir.IntType(64), 0)
    else:
        # Local struct
        var_ptr = self.builder.alloca(ir.IntType(64), name=node.name)
    
    # Store the variable and mark its type as a struct
    self.declare_variable(node.name, var_ptr, struct_type_name)


def generate_struct_field_access(self, node):
    """
    Generate code for accessing a struct field.
    """
    # Get struct variable information
    struct_name = node.struct_name
    struct_type_name = self.get_variable_type(struct_name)
    
    # Check if struct type exists
    if not Type.is_struct_type(struct_type_name):
        raise ValueError(f"Variable {struct_name} is not a struct")
    
    # Get field information
    field_name = node.field_name
    
    # This is a placeholder implementation using the same approach as field assignment
    # Get the field variable using the composite name pattern
    composite_name = f"{struct_name}.{field_name}"
    field_ptr = self.get_variable(composite_name)
    
    # Load and return the field value
    return self.builder.load(field_ptr, name=f"{composite_name}_value")


def generate_struct_field_assign(self, node):
    """
    Generate code for assigning a value to a struct field.
    """
    # Get struct variable information
    struct_name = node.struct_name
    struct_ptr = self.get_variable(struct_name)
    struct_type_name = self.get_variable_type(struct_name)
    
    # Check if struct type exists
    if not Type.is_struct_type(struct_type_name):
        raise ValueError(f"Variable {struct_name} is not a struct")
    
    # Get field information
    field_name = node.field_name
    
    # This is a placeholder implementation - in a real implementation
    # we'd calculate the actual field offset in memory
    
    # For now, we'll create a separate global/local variable for each struct field
    # with the name pattern "struct_name.field_name"
    composite_name = f"{struct_name}.{field_name}"
    
    # Check if this field variable already exists
    field_ptr = None
    try:
        field_ptr = self.get_variable(composite_name)
    except ValueError:
        # Create the field variable
        field_type = Type.get_struct_field_type(struct_type_name, field_name)
        field_ir_type = Type.get_ir_type(field_type)
        
        if self.builder is None:
            # Global scope
            field_ptr = ir.GlobalVariable(self.module, field_ir_type, name=composite_name)
            field_ptr.initializer = ir.Constant(field_ir_type, 0)
        else:
            # Local scope
            field_ptr = self.builder.alloca(field_ir_type, name=composite_name)
            
        # Register the field variable
        self.declare_variable(composite_name, field_ptr, field_type)
    
    # Generate the value to assign
    from codegen.expression import generate_expression
    value = generate_expression(self, node.value)
    
    # Ensure compatible types
    field_type = Type.get_struct_field_type(struct_type_name, field_name)
    field_ir_type = Type.get_ir_type(field_type)
    
    # Convert if needed
    from codegen.type_utils import convert_value_to_type
    value = convert_value_to_type(self, value, field_ir_type)
    
    # Store the value
    self.builder.store(value, field_ptr) 