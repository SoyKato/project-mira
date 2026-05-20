from supabase import create_client

SUPABASE_URL = "https://rifdbtcnyrwhkqardjxd.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpZmRidGNueXJ3aGtxYXJkanhkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzE4NDMzMSwiZXhwIjoyMDg4NzYwMzMxfQ.bZkeBAsNy2YQzkkhzIhGStgzqFrahV_u_21H3cDl2BE"


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)