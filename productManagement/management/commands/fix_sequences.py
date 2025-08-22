from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix database sequences for all ProductManagement models'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # First, get all existing sequences that match our pattern
            cursor.execute("""
                SELECT sequencename 
                FROM pg_sequences 
                WHERE schemaname = 'public' 
                AND (sequencename LIKE '%productmanagement%' OR sequencename LIKE '%productManagement%')
                ORDER BY sequencename;
            """)
            
            sequences = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"Found ProductManagement sequences: {sequences}")
            
            # Map sequences to their likely table names
            sequence_table_map = {
                'productmanagement_productmetadata_id_seq': 'productManagement_productmetadata',
                'productManagement_products_id_seq': 'productManagement_products',
                'productManagement_categories_id_seq': 'productManagement_categories',
                'productManagement_productimage_id_seq': 'productManagement_productimage',
            }
            
            fixed_count = 0
            
            for sequence_name in sequences:
                table_name = sequence_table_map.get(sequence_name)
                
                if table_name:
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
                            # Get current max ID
                            cursor.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}";')
                            max_id = cursor.fetchone()[0]
                            
                            # Get current sequence value - use quotes for case-sensitive names
                            cursor.execute(f'SELECT last_value FROM "{sequence_name}";')
                            current_seq = cursor.fetchone()[0]
                            
                            # Only reset if sequence is behind or equal to the max ID
                            if current_seq <= max_id:
                                # Reset sequence - use quotes for case-sensitive names
                                cursor.execute(f'SELECT setval(%s, %s);', [f'"{sequence_name}"', max_id + 1])
                                
                                # Verify the fix
                                cursor.execute(f'SELECT last_value FROM "{sequence_name}";')
                                new_val = cursor.fetchone()[0]
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✓ Fixed {table_name}: max_id={max_id}, old_seq={current_seq}, new_seq={new_val}'
                                    )
                                )
                                fixed_count += 1
                            else:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✓ {table_name} is already correct: max_id={max_id}, seq={current_seq}'
                                    )
                                )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'⚠ Table {table_name} does not exist for sequence {sequence_name}')
                            )
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Error fixing {sequence_name}: {str(e)}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ No table mapping found for sequence {sequence_name}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'Sequence fixing completed! Fixed {fixed_count} sequences.')
            )

            # Also show all ProductManagement tables that exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%product%'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"\nExisting ProductManagement tables: {tables}")