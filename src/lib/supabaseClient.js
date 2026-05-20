import { createClient } from '@supabase/supabase-js'

// Credenciales directas (para evitar problemas de variables de entorno)
const supabaseUrl = 'https://rifdbtcnyrwhkqardjxd.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpZmRidGNueXJ3aGtxYXJkanhkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxODQzMzEsImV4cCI6MjA4ODc2MDMzMX0.UlExG1dF-PEi5oW79l1HPOfO5wDnEW6GLKeWQZNDwdc'

// Crear el cliente
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

console.log('✅ Supabase client inicializado')