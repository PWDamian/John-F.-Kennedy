from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_assign(self, node):
    ptr = self.get_variable(node.name)
    if not ptr:
        raise ValueError(f"Variable {node.name} not declared")

    var_type = self.get_variable_type(node.name)
    var_type = Type.map_to_internal_type(var_type)

    value = expression.generate_expression(self, node.value)

    if var_type == Type.STRING:
        if not hasattr(self, 'strcpy'):
            strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                        [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
            self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

        dest_ptr = self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))
        self.builder.call(self.strcpy, [dest_ptr, value])
    else:
        value = type_utils.convert_if_needed(self, value, var_type)
        self.builder.store(value, ptr)


def generate_declare_assign(self, node):
    is_global = self.func is None or self.func.name == "main" and len(self.scopes) == 1

    # Special handling for class types
    if hasattr(self, 'class_declarations') and node.type in self.class_declarations:
        # This is a class variable declaration
        class_decl = self.class_declarations[node.type]
        
        # Make sure we have the class struct type before using it
        if not class_decl.ir_struct_type:
            class_decl.get_ir_type(self.module)
            
        # Get the LLVM struct type directly
        struct_type = class_decl.ir_struct_type
        
        if is_global:
            # For global variables, create a global struct directly
            global_var = ir.GlobalVariable(self.module, struct_type, name=node.name)
            
            # Create element initializers - zero for all elements
            zeros = []
            for elem_type in struct_type.elements:
                zeros.append(ir.Constant(elem_type, 0))
                
            # Create initializer for the struct
            zero_init = ir.Constant(struct_type, zeros)
            global_var.initializer = zero_init
            global_var.linkage = 'common'
            
            # Store in the symbol table
            self.declare_variable(node.name, global_var, node.type)
        else:
            # Local variable - allocate the struct directly
            ptr = self.builder.alloca(struct_type, name=node.name)
            
            # Initialize fields to zero if needed
            for i, elem_type in enumerate(struct_type.elements):
                # Get pointer to field
                indices = [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)]
                field_ptr = self.builder.gep(ptr, indices, inbounds=True)
                
                # Initialize to zero
                zero = ir.Constant(elem_type, 0)
                self.builder.store(zero, field_ptr)
            
            # Store in the symbol table
            self.declare_variable(node.name, ptr, node.type)
        
        return
    
    # Original code for non-class types
    if node.type == Type.STRING:
        if is_global:
            string_type = ir.ArrayType(ir.IntType(8), 256)
            global_var = ir.GlobalVariable(self.module, string_type, name=node.name)
            global_var.initializer = ir.Constant(string_type, bytearray(256))  # Initialize to zero
            global_var.linkage = 'common'

            self.declare_variable(node.name, global_var, Type.STRING)

            if node.value:
                value = expression.generate_expression(self, node.value)

                if not hasattr(self, 'strcpy'):
                    strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                                [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                    self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

                ptr = self.builder.bitcast(global_var, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.strcpy, [ptr, value])
        else:
            buffer = self.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=node.name)
            ptr = self.builder.bitcast(buffer, ir.PointerType(ir.IntType(8)))
            self.declare_variable(node.name, buffer, node.type)

            if node.value:
                value = expression.generate_expression(self, node.value)

                if not hasattr(self, 'strcpy'):
                    strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                                [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                    self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

                self.builder.call(self.strcpy, [ptr, value])
    else:
        internal_type = Type.map_to_internal_type(node.type)
        llvm_type = Type.get_ir_type(internal_type)

        if is_global:
            global_var = ir.GlobalVariable(self.module, llvm_type, name=node.name)

            if node.value:
                value = expression.generate_expression(self, node.value)
                value = type_utils.convert_if_needed(self, value, internal_type)
                if isinstance(value, ir.Constant):
                    global_var.initializer = value
                else:
                    global_var.initializer = ir.Constant(llvm_type, 0)
                    self.builder.store(value, global_var)
            else:
                global_var.initializer = ir.Constant(llvm_type, 0)

            self.declare_variable(node.name, global_var, internal_type)
        else:
            ptr = self.builder.alloca(llvm_type, name=node.name)
            self.declare_variable(node.name, ptr, internal_type)

            if node.value:
                value = expression.generate_expression(self, node.value)
                value = type_utils.convert_if_needed(self, value, internal_type)
                self.builder.store(value, ptr)
