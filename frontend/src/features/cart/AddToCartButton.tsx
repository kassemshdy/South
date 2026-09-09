import { Check, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent } from '@/components/ui/Dialog'
import { useCart, type Cart, type CartLine } from '@/features/cart/CartContext'
import { useT } from '@/i18n'

/**
 * Put a product in the order being collected.
 *
 * The dialog exists because of the one-business rule: an order spanning two
 * shops has no meaning when one owner has to fulfil it, so switching
 * listings discards what was collected. Doing that silently would lose
 * someone's work; the alternative — merging — would produce an order nobody
 * can fulfil. So it is a question, asked only when it actually arises.
 */
export function AddToCartButton({
  target,
  line,
  block = false,
}: {
  target: Omit<Cart, 'lines'>
  line: CartLine
  block?: boolean
}) {
  const t = useT()
  const { add, replaceWith } = useCart()
  const [conflict, setConflict] = useState(false)
  const [added, setAdded] = useState(false)

  const onAdd = () => {
    if (add(target, line)) {
      setAdded(true)
      return
    }
    setConflict(true)
  }

  return (
    <>
      {added ? (
        <Button asChild variant="outline" block={block}>
          <Link to="/cart">
            <Check className="h-4 w-4" aria-hidden="true" />
            {t('cart.viewOrder')}
          </Link>
        </Button>
      ) : (
        <Button type="button" onClick={onAdd} block={block}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('cart.add')}
        </Button>
      )}

      <Dialog open={conflict} onOpenChange={setConflict}>
        <DialogContent
          title={t('cart.otherBusinessTitle')}
          description={t('cart.otherBusinessBody', { name: target.businessName })}
        >
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => {
                replaceWith(target, line)
                setConflict(false)
                setAdded(true)
              }}
            >
              {t('cart.startNew')}
            </Button>
            <Button variant="ghost" onClick={() => setConflict(false)}>
              {t('cart.keepCurrent')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
