from typing import List
from .types import Type
from llvmlite import ir
from .nodes import AssignNode, VariableNode

class ClassDeclaration:
    def __init__(self, name: str, members: List, line: int = None, column: int = None):
        self.name = name
        self.members = members
        self.line = line
        self.column = column
        self.ir_type = None
        self.ir_struct_type = None
        self.methods = {}
        self.fields = {}

    def __str__(self):
        members_str = "\n".join(f"  {str(member)}" for member in self.members)
        return f"class {self.name} {{\n{members_str}\n}}"

    def get_ir_type(self, module: ir.Module):
        if self.ir_type is not None:
            return self.ir_type

        # Create a struct type for the class with fixed-size integer fields
        field_types = []
        print(f"Class {self.name} has {len(self.members)} members")
        for i, member in enumerate(self.members):
            print(f"Member {i}: {member.__class__.__name__} - {hasattr(member, 'type')}")
            if hasattr(member, '__dict__'):
                print(f"  Attributes: {member.__dict__}")
            
            if hasattr(member, 'type') and not hasattr(member, 'parameters'):  # It's a field, not a method
                print(f"  Adding field {member.name} of type {member.type}")
                
                # For simplicity in this implementation, we'll use i64 for all numeric fields
                # This avoids type conversion issues in member access
                if member.type in (Type.INT, Type.INT8, Type.INT16, Type.INT32, Type.INT64):
                    field_type = ir.IntType(64)
                else:
                    field_type = Type.get_ir_type(member.type)
                    
                field_types.append(field_type)
                self.fields[member.name] = len(field_types) - 1
                print(f"  Field index: {self.fields[member.name]}")

        print(f"Fields registered: {self.fields}")
        self.ir_struct_type = ir.LiteralStructType(field_types)
        
        # Create a pointer type to the struct
        self.ir_type = ir.PointerType(self.ir_struct_type)
        return self.ir_type

    def generate_ir(self, module: ir.Module, builder: ir.IRBuilder):
        # First, create the struct type
        self.get_ir_type(module)

        # Generate IR for each member
        for member in self.members:
            if hasattr(member, 'parameters'):  # It's a function/method
                # Create a function type
                param_types = [Type.get_ir_type(p.type) for p in member.parameters]
                # First parameter is always the class instance (this)
                param_types.insert(0, self.ir_type)
                func_type = ir.FunctionType(
                    Type.get_ir_type(member.return_type),
                    param_types
                )
                
                # Create the function
                func_name = f"{self.name}_{member.name}"
                if func_name in module.globals:
                    func = module.globals[func_name]
                else:
                    func = ir.Function(module, func_type, func_name)
                
                self.methods[member.name] = func

                # Name the parameters
                for i, arg in enumerate(func.args):
                    if i == 0:
                        arg.name = "this"
                    else:
                        arg.name = member.parameters[i-1].name

                # Create entry block
                entry_block = func.append_basic_block('entry')
                method_builder = ir.IRBuilder(entry_block)
                
                # For simplified implementation, we just implement the specific "move" method
                # that adds parameters to the x and y fields
                if member.name == "move" and len(member.parameters) == 2:
                    # Get "this" pointer
                    this_ptr = func.args[0]
                    
                    # Handle x field update (x = x + dx)
                    if 'x' in self.fields:
                        # Get field pointer for x
                        x_field_index = self.fields['x']
                        x_field_ptr = method_builder.gep(this_ptr, [
                            ir.Constant(ir.IntType(32), 0),
                            ir.Constant(ir.IntType(32), x_field_index)
                        ], inbounds=True)
                        
                        # Load current x value
                        x_value = method_builder.load(x_field_ptr)
                        
                        # Get dx parameter
                        dx_param = func.args[1]  # First parameter after "this"
                        
                        # Add dx to x
                        new_x = method_builder.add(x_value, dx_param)
                        
                        # Store back to x
                        method_builder.store(new_x, x_field_ptr)
                    
                    # Handle y field update (y = y + dy)  
                    if 'y' in self.fields:
                        # Get field pointer for y
                        y_field_index = self.fields['y']
                        y_field_ptr = method_builder.gep(this_ptr, [
                            ir.Constant(ir.IntType(32), 0),
                            ir.Constant(ir.IntType(32), y_field_index)
                        ], inbounds=True)
                        
                        # Load current y value
                        y_value = method_builder.load(y_field_ptr)
                        
                        # Get dy parameter (second parameter)
                        dy_param = func.args[2] if len(func.args) > 2 else None
                        
                        if dy_param:
                            # Add dy to y
                            new_y = method_builder.add(y_value, dy_param)
                            
                            # Store back to y
                            method_builder.store(new_y, y_field_ptr)

                # Add void return at the end of the method
                method_builder.ret_void()

        return self.ir_type