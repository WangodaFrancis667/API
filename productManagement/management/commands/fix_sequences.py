from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix database sequences for all ProductManagement models'

    def handle(self, *args, **options):
        # Updated with the correct sequence names from your database
        tables_to_fix = [
            ('productManagement_productmetadata', 'productmanagement_productmetadata_id_seq'),  # Note: lowercase sequence name
            ('productManagement_products', 'productManagement_products_id_seq'),
            ('productManagement_categories', 'productManagement_categories_id_seq'),
            ('productManagement_productimage', 'productManagement_productimage_id_seq'),
        ]
        
        with connection.cursor() as cursor:
            for table_name, sequence_name in tables_to_fix:
                try:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        );
                    """, [table_name])
                    
                    if cursor.fetchone()[0]:
                        # Check if sequence exists
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.sequences 
                                WHERE sequence_schema = 'public' 
                                AND sequence_name = %s
                            );
                        """, [sequence_name])
                        
                        if cursor.fetchone()[0]:
                            # Get current max ID
                            cursor.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}";')
                            max_id = cursor.fetchone()[0]
                            
                            # Get current sequence value
                            cursor.execute('SELECT last_value FROM "' + sequence_name + '";')
                            current_seq = cursor.fetchone()[0]
                            
                            # Reset sequence
                            cursor.execute('SELECT setval(%s, %s);', [sequence_name, max_id + 1])
                            
                            # Verify the fix
                            cursor.execute('SELECT last_value FROM "' + sequence_name + '";')
                            new_val = cursor.fetchone()[0]
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Fixed {table_name}: max_id={max_id}, old_seq={current_seq}, new_seq={new_val}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'⚠ Sequence {sequence_name} does not exist')
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠ Table {table_name} does not exist')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error fixing {table_name}: {str(e)}')
                    )

        self.stdout.write(self.style.SUCCESS('Sequence fixing completed!'))