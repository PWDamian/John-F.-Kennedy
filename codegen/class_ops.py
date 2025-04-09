from llvmlite import ir
from ast2.class_nodes import ClassDeclaration
from ast2.nodes import MemberAccessNode, MemberAssignNode
from codegen import expression

def generate_class_declaration(codegen, node: ClassDeclaration):
    # Generate the class type and methods
    node.generate_ir(codegen.module, codegen.builder)
    
    # Store the class type in the global scope
    codegen.global_variables[node.name] = (node.ir_type, node.ir_type)
    
    # Store the class declaration for later use
    if not hasattr(codegen, 'class_declarations'):
        codegen.class_declarations = {}
    
    codegen.class_declarations[node.name] = node

def generate_class_instantiation(codegen, class_name: str):
    # Get the class type
    class_type = codegen.get_variable_type(class_name)
    
    # Allocate memory for the class instance
    instance = codegen.builder.alloca(class_type)
    
    # Initialize fields to default values
    class_decl = codegen.global_variables[class_name][0]
    for field_name, field_index in class_decl.fields.items():
        field_ptr = codegen.builder.gep(instance, [ir.Constant(ir.IntType(32), 0), 
                                                 ir.Constant(ir.IntType(32), field_index)])
        # Initialize to zero
        codegen.builder.store(ir.Constant(class_decl.ir_struct_type.elements[field_index], 0), field_ptr)
    
    return instance

def generate_method_call(codegen, instance, class_name, method_name, args: list):
    # Find the class declaration
    if not hasattr(codegen, 'class_declarations'):
        codegen.class_declarations = {}
        
    class_decl = None
    if class_name in codegen.class_declarations:
        class_decl = codegen.class_declarations[class_name]
    
    if not class_decl:
        raise ValueError(f"Cannot find class declaration for type {class_name}")
    
    # Check if the class has the method
    if not hasattr(class_decl, 'methods') or method_name not in class_decl.methods:
        raise ValueError(f"Class {class_name} does not have method {method_name}")
    
    # Get the method function
    method_func = class_decl.methods[method_name]
    
    # Make sure we have the right instance type
    # For struct types (global variables), we need to get a pointer to them
    # because methods expect a pointer to the struct as 'this'
    instance_ptr = instance
    if not isinstance(instance.type, ir.PointerType):
        # For global variables (direct structs), create a pointer
        tmp_ptr = codegen.builder.alloca(instance.type)
        codegen.builder.store(instance, tmp_ptr)
        instance_ptr = tmp_ptr
    
    # Prepare arguments (instance is the first argument)
    all_args = [instance_ptr] + args
    
    # Call the method
    return codegen.builder.call(method_func, all_args, name=f"{class_name}_{method_name}_call")

def generate_member_access(codegen, node: MemberAccessNode):
    # Get the object instance
    instance = codegen.get_variable(node.object_name)
    
    # Get the class name
    class_name = codegen.get_variable_type(node.object_name)
    
    # Find the class declaration using our new mechanism
    if not hasattr(codegen, 'class_declarations'):
        codegen.class_declarations = {}
        
    # Try to find the class declaration
    class_decl = None
    if class_name in codegen.class_declarations:
        class_decl = codegen.class_declarations[class_name]
    
    if not class_decl:
        raise ValueError(f"Cannot find class declaration for {node.object_name} (type: {class_name})")
    
    # Check if it's a field access
    if hasattr(class_decl, 'fields') and node.member_name in class_decl.fields:
        # Make sure we have the class struct type before using it
        if not class_decl.ir_struct_type:
            class_decl.get_ir_type(codegen.module)
            
        # Get the field index
        field_index = class_decl.fields[node.member_name]
        
        # Get the field type
        field_type = class_decl.ir_struct_type.elements[field_index]
        
        # Get field pointer based on whether it's a global or local variable
        field_ptr = None
        
        if isinstance(instance.type, ir.PointerType):
            # For local variables (pointers to structs)
            indices = [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), field_index)]
            field_ptr = codegen.builder.gep(instance, indices, name=f"{node.object_name}.{node.member_name}", inbounds=True)
        else:
            # For global variables (structs directly)
            indices = [ir.Constant(ir.IntType(32), field_index)]
            field_ptr = codegen.builder.gep(instance, indices, name=f"{node.object_name}.{node.member_name}", inbounds=True)
        
        # Load the field value
        return codegen.builder.load(field_ptr, name=f"{node.object_name}.{node.member_name}.load")
    
    # If it's not a field, it must be a method call
    # This will be handled by the function call code
    return instance

def generate_member_assign(codegen, node: MemberAssignNode):
    # Get the object instance
    instance = codegen.get_variable(node.object_name)
    
    # Get the class name
    class_name = codegen.get_variable_type(node.object_name)
    
    # Find the class declaration using our new mechanism
    if not hasattr(codegen, 'class_declarations'):
        codegen.class_declarations = {}
        
    # Try to find the class declaration
    class_decl = None
    if class_name in codegen.class_declarations:
        class_decl = codegen.class_declarations[class_name]
    
    if not class_decl:
        raise ValueError(f"Cannot find class declaration for {node.object_name} (type: {class_name})")
    
    # Get the field index
    if not hasattr(class_decl, 'fields'):
        raise ValueError(f"Class {class_name} does not have fields attribute")
    
    field_index = class_decl.fields[node.member_name]
    
    # Make sure we have the class struct type before using it
    if not class_decl.ir_struct_type:
        class_decl.get_ir_type(codegen.module)
    
    # Get field pointer - use the struct type directly, not through a pointer
    field_ptr = None
    
    # Get the target field type
    field_type = class_decl.ir_struct_type.elements[field_index]
    
    # Create indices for GEP
    if isinstance(instance.type, ir.PointerType):
        # For local variables (pointers to structs)
        indices = [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), field_index)]
        field_ptr = codegen.builder.gep(instance, indices, name=f"{node.object_name}.{node.member_name}", inbounds=True)
    else:
        # For global variables (structs directly)
        indices = [ir.Constant(ir.IntType(32), field_index)]
        field_ptr = codegen.builder.gep(instance, indices, name=f"{node.object_name}.{node.member_name}", inbounds=True)
    
    # Generate the value to store and make sure it's the right type
    value = expression.generate_expression(codegen, node.value)
    
    # Convert value to the correct type if needed
    if value.type != field_type:
        if isinstance(field_type, ir.IntType) and isinstance(value.type, ir.IntType):
            if field_type.width > value.type.width:
                value = codegen.builder.sext(value, field_type)
            elif field_type.width < value.type.width:
                value = codegen.builder.trunc(value, field_type)
        elif field_type.is_pointer and isinstance(value.type, ir.IntType):
            # Handle storing to pointer type (like i8*)
            # We need to convert the integer to the pointed-to type first
            pointed_type = field_type.pointee
            if isinstance(pointed_type, ir.IntType):
                # Convert the integer value to match the pointed-to type
                if pointed_type.width != value.type.width:
                    if pointed_type.width > value.type.width:
                        value = codegen.builder.sext(value, pointed_type)
                    else:
                        value = codegen.builder.trunc(value, pointed_type)
            # Now we handle the pointer storage
            tmp_ptr = codegen.builder.alloca(pointed_type)
            codegen.builder.store(value, tmp_ptr)
            value = tmp_ptr
    
    # Store the value
    codegen.builder.store(value, field_ptr) 