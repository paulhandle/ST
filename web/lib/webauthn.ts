type JsonObject = Record<string, unknown>

function base64urlToBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  const binary = window.atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

function bufferToBase64url(value: ArrayBuffer): string {
  const bytes = new Uint8Array(value)
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return window.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function decodeCredentialDescriptor(item: JsonObject): PublicKeyCredentialDescriptor {
  return {
    ...item,
    id: base64urlToBuffer(String(item.id)),
  } as PublicKeyCredentialDescriptor
}

function decodePublicKeyCreationOptions(options: JsonObject): PublicKeyCredentialCreationOptions {
  const user = options.user as JsonObject
  return {
    ...options,
    challenge: base64urlToBuffer(String(options.challenge)),
    user: {
      ...user,
      id: base64urlToBuffer(String(user.id)),
    },
    excludeCredentials: Array.isArray(options.excludeCredentials)
      ? options.excludeCredentials.map(item => decodeCredentialDescriptor(item as JsonObject))
      : undefined,
  } as PublicKeyCredentialCreationOptions
}

function decodePublicKeyRequestOptions(options: JsonObject): PublicKeyCredentialRequestOptions {
  return {
    ...options,
    challenge: base64urlToBuffer(String(options.challenge)),
    allowCredentials: Array.isArray(options.allowCredentials)
      ? options.allowCredentials.map(item => decodeCredentialDescriptor(item as JsonObject))
      : undefined,
  } as PublicKeyCredentialRequestOptions
}

function encodeAuthenticatorAttestationResponse(response: AuthenticatorAttestationResponse) {
  return {
    clientDataJSON: bufferToBase64url(response.clientDataJSON),
    attestationObject: bufferToBase64url(response.attestationObject),
    transports: typeof response.getTransports === 'function' ? response.getTransports() : [],
  }
}

function encodeAuthenticatorAssertionResponse(response: AuthenticatorAssertionResponse) {
  return {
    clientDataJSON: bufferToBase64url(response.clientDataJSON),
    authenticatorData: bufferToBase64url(response.authenticatorData),
    signature: bufferToBase64url(response.signature),
    userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
  }
}

export async function createPasskeyCredential(options: JsonObject) {
  const credential = await navigator.credentials.create({
    publicKey: decodePublicKeyCreationOptions(options),
  })
  if (!(credential instanceof PublicKeyCredential)) {
    throw new Error('Passkey registration was cancelled.')
  }
  const response = credential.response
  if (!(response instanceof AuthenticatorAttestationResponse)) {
    throw new Error('Passkey registration response was invalid.')
  }
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: encodeAuthenticatorAttestationResponse(response),
  }
}

export async function getPasskeyCredential(options: JsonObject) {
  const credential = await navigator.credentials.get({
    publicKey: decodePublicKeyRequestOptions(options),
  })
  if (!(credential instanceof PublicKeyCredential)) {
    throw new Error('Passkey sign-in was cancelled.')
  }
  const response = credential.response
  if (!(response instanceof AuthenticatorAssertionResponse)) {
    throw new Error('Passkey sign-in response was invalid.')
  }
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: encodeAuthenticatorAssertionResponse(response),
  }
}
