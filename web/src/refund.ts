type RefundRequest = {
  paymentId: string
  accountId: string
  amount: string
  reason?: string
}

type RefundResponse = {
  status: string
  amount: string
  reason?: string
}

export async function submitManualRefund(input: RefundRequest): Promise<RefundResponse> {
  const response = await fetch("/admin/refunds", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      payment_id: input.paymentId,
      account_id: input.accountId,
      amount: Number(input.amount).toString(),
      reason: input.reason,
    }),
  })

  if (!response.ok) {
    return response.json()
  }

  return response.json()
}

export function formatRefundStatus(response: RefundResponse): string {
  return `${response.status}: ${response.amount}`
}