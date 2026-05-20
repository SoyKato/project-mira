import { ref, computed } from 'vue'
import { supabase } from '@/lib/supabaseClient'

const _user = ref(null)
const _isLoggedIn = ref(false)

export function useAuth() {
  const user = computed(() => _user.value)
  const isAuthenticated = computed(() => _isLoggedIn.value)

  function setUser(u) {
    _user.value = {
      name: u.user_metadata?.name || u.email?.split('@')[0],
      email: u.email
    }
  }

  function clearUser() {
    _user.value = null
    _isLoggedIn.value = false
    localStorage.removeItem('logged_in')
  }


  async function login(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })

    if (error) return { ok: false, error: error.message }

    setUser(data.user)

    _isLoggedIn.value = true
    localStorage.setItem('logged_in', 'true')

    return { ok: true }
  }

  async function register(name, email, password) {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { name },
        emailRedirectTo: 'http://localhost:5173/login'
      }
    })

    if (error) return { ok: false, error: error.message }



    return { ok: true }
  }

  async function logout() {
    await supabase.auth.signOut()
    clearUser()
  }

  if (localStorage.getItem('logged_in') === 'true') {
    _isLoggedIn.value = true
  }

  return {
    user,
    isAuthenticated,
    login,
    logout,
    register
  }
}

// este arregla el dashboard