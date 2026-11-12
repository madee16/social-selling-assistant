import client from './client';

export async function uploadProductImage(file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/api/uploads/product-image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
